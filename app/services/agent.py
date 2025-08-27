from __future__ import annotations

from typing import Any, Tuple, Optional
import json
from typing import AsyncIterator, Dict, Any, List
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
try:
	from langchain_core.messages import ToolMessage  # type: ignore
except Exception:  # pragma: no cover
	ToolMessage = None  # type: ignore

from app.config import settings
from app.services.tools import build_tools
import json as _json


SYSTEM_PROMPT = (
	"You are Startup Mentor Agent.\n"
	"Goal: Help founders assess their startup idea and provide crisp, high-signal insights.\n"
	"Instructions:\n"
	"- Maintain a concise, structured conversation.\n"
	"- If the user's description is incomplete, ask targeted questions to fill gaps.\n"
	"- Only call the analysis tool when you have: a clear startup description, a chosen analysis_mode (default 'advanced'), and include_external_research (default true).\n"
	"- When you use the tool, reply with a short summary (max 2-3 sentences) and a clear recommendation. Do NOT enumerate detailed findings; the detailed output will be available via tool actions.\n"
	"- Keep answers brief and high-level.\n"
	"- Keep history in mind and avoid repeating previous questions.\n"
)


def build_agent():
	llm = ChatOpenAI(
		openai_api_key=settings.OPENAI_API_KEY,
		model=settings.MODEL_NAME,
		temperature=0.2,
		streaming=True,
	)
	tools = build_tools()
	agent = create_react_agent(llm, tools, messages_modifier=SYSTEM_PROMPT)
	return agent


def _gather_messages_from_update(obj: Any) -> List[Any]:
	collected: List[Any] = []
	if obj is None:
		return collected
	if hasattr(obj, "type") and hasattr(obj, "content"):
		collected.append(obj)
		return collected
	if isinstance(obj, dict):
		for v in obj.values():
			collected.extend(_gather_messages_from_update(v))
		return collected
	if isinstance(obj, (list, tuple)):
		for v in obj:
			collected.extend(_gather_messages_from_update(v))
		return collected
	return collected


def _safe_content(content: Any) -> Any:
	if isinstance(content, str):
		try:
			parsed = _json.loads(content)
			return parsed
		except Exception:
			return content
	return content


def _extract_tool_starts(msg: Any) -> List[Dict[str, Any]]:
	events: List[Dict[str, Any]] = []
	if isinstance(msg, AIMessage):
		tool_calls = getattr(msg, "tool_calls", None)
		if not tool_calls and hasattr(msg, "additional_kwargs"):
			ak = getattr(msg, "additional_kwargs") or {}
			tool_calls = ak.get("tool_calls")
			# legacy single function_call
			if not tool_calls and ak.get("function_call"):
				fc = ak["function_call"]
				name = fc.get("name") if isinstance(fc, dict) else getattr(fc, "name", None)
				args_raw = fc.get("arguments") if isinstance(fc, dict) else getattr(fc, "arguments", None)
				args = args_raw
				if isinstance(args_raw, str):
					try:
						args = _json.loads(args_raw)
					except Exception:
						args = args_raw
				events.append({"type": "tool_start", "role": "tool", "content": args, "tool_name": name})
				return events
		if tool_calls:
			for call in tool_calls:
				fn = None
				if isinstance(call, dict):
					fn = call.get("function")
				elif hasattr(call, "function"):
					fn = getattr(call, "function")
				name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", None)
				args_raw = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", None)
				args = args_raw
				if isinstance(args_raw, str):
					try:
						args = _json.loads(args_raw)
					except Exception:
						args = args_raw
				events.append({"type": "tool_start", "role": "tool", "content": args, "tool_name": name})
	return events


async def stream_agent_events(agent, messages: List[dict]) -> AsyncIterator[Dict[str, Any]]:
	"""Stream agent steps; yields dict events suitable for SSE JSON serialization.
	Emits one event per new message (human/assistant/tool) using 'updates' mode, and includes tool_start events."""
	lc_messages = []
	for m in messages:
		role = m.get("role")
		content = m.get("content", "")
		if role == "system":
			lc_messages.append(SystemMessage(content=content))
		elif role == "assistant":
			lc_messages.append(AIMessage(content=content))
		else:
			lc_messages.append(HumanMessage(content=content))

	output = {
		"ai_output": "",
		"action": None
	}

	async for update in agent.astream({"messages": lc_messages}, stream_mode="updates"):
		print(update)
		print("--------------------------------")
		print()
		res = update
		if 'agent' in res:  
			ai_message = res['agent']['messages'][0].content
			if len(ai_message)>0:
				print(ai_message)
			output["ai_output"] = ai_message
			if extract_tool_call(res)[0]:
				output["action"] = {
					"tool": extract_tool_call(res)[0],
					"tool_input": extract_tool_call(res)[1],
					"tool_output": ""
				}
			else:
				output["action"] = []

		if 'tools' in res:
			tool_output = res['tools']['messages'][0].content
			output["action"]['tool_output'] = tool_output
			
		yield output



def extract_tool_call(data: dict) -> Tuple[Optional[str], Optional[dict]]:
	"""
	Returns (tool_name, tool_input_dict) or (None, None) if not found.
	Handles both OpenAI function-call formats:
	- message.tool_calls: [{'name': str, 'args': dict}] or [{'function': {'name': str, 'arguments': str}}]
	- message.additional_kwargs.tool_calls / .function_call
	"""
	messages = (data or {}).get('agent', {}).get('messages', [])
	for msg in messages:
		# Case 1: message is a plain dict
		if isinstance(msg, dict):
			# Prefer modern tool_calls on message
			tool_calls = msg.get('tool_calls')
			# Fallback to additional_kwargs.tool_calls
			if not tool_calls:
				tool_calls = (msg.get('additional_kwargs') or {}).get('tool_calls')

			# Legacy single function_call under additional_kwargs
			if not tool_calls:
				fc = (msg.get('additional_kwargs') or {}).get('function_call')
				if fc:
					name = fc.get('name')
					args_raw = fc.get('arguments')
					args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
					return name, args

			if tool_calls:
				call = tool_calls[0]
				# Variant: {'name': ..., 'args': {...}}
				if isinstance(call, dict) and 'name' in call and 'args' in call:
					return call['name'], call['args']
				# Variant: {'function': {'name': ..., 'arguments': '...json...'}}
				fn = call.get('function') if isinstance(call, dict) else None
				if fn:
					name = fn.get('name')
					args_raw = fn.get('arguments')
					args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
					return name, args

		# Case 2: message is an object (e.g., AIMessage)
		else:
			tool_calls = getattr(msg, 'tool_calls', None)

			# Fallback to additional_kwargs.tool_calls / function_call
			if not tool_calls:
				ak = getattr(msg, 'additional_kwargs', {}) or {}
				tool_calls = ak.get('tool_calls')
				if not tool_calls and ak.get('function_call'):
					fc = ak['function_call']
					if isinstance(fc, dict):
						name = fc.get('name')
						args_raw = fc.get('arguments')
					else:
						name = getattr(fc, 'name', None)
						args_raw = getattr(fc, 'arguments', None)
					args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
					return name, args

			if tool_calls:
				call = tool_calls[0]
				# Dict form
				if isinstance(call, dict):
					if 'name' in call and 'args' in call:
						return call['name'], call['args']
					fn = call.get('function')
					if fn:
						name = fn.get('name')
						args_raw = fn.get('arguments')
						args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
						return name, args
				# Object form with .function
				fn = getattr(call, 'function', None)
				if fn is not None:
					name = getattr(fn, 'name', None)
					args_raw = getattr(fn, 'arguments', None)
					args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
					return name, args

	return None, None