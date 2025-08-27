from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi_sse import sse_handler
from pydantic import BaseModel
from typing import Any
import json

from app.models.schemas import ChatPostRequest, TokenResponse, ConversationMessage
from app.services.stores import conversation_store, token_store, now_utc
from app.services.agent import build_agent, stream_agent_events
from app.config import settings


class ToolAction(BaseModel):
	tool: str | None = None
	tool_input: Any | None = None
	tool_output: Any | None = None


class UnifiedEvent(BaseModel):
	user_id: int
	conversationId: int
	output: str | None = None
	action: ToolAction


router = APIRouter()
_agent = None


def _get_agent():
	global _agent
	if _agent is None:
		_agent = build_agent()
	return _agent


@router.post("/message", response_model=TokenResponse)
async def post_message(body: ChatPostRequest):
	conv = conversation_store.get_or_create(body.user_id, body.conversation_id)
	conv.append(ConversationMessage(role="user", content=body.text, timestamp=now_utc()))
	pending = token_store.issue_token(body.user_id, body.conversation_id, body.text)
	return TokenResponse(token=pending.token, expires_in=settings.TOKEN_TTL_SECONDS)


@router.get("/stream")
@sse_handler()
async def stream(token: str = Query(...)):
	pending = token_store.pop(token)
	if not pending:
		raise HTTPException(status_code=404, detail="Invalid or expired token")

	user_id = pending.user_id
	conversation_id = pending.conversation_id
	conv = conversation_store.get_or_create(user_id, conversation_id)

	messages = [
		{"role": m.role, "content": m.content}
		for m in conv.messages
	]

	if not settings.OPENAI_API_KEY:
		yield UnifiedEvent(
			user_id=user_id,
			conversationId=conversation_id,
			output="",
			action=ToolAction(),
		)
		return

	agent = _get_agent()

	last_assistant: str | None = None


	async for event in stream_agent_events(agent, messages):
		last_assistant = event
		
		# Convert action to ToolAction object
		action_data = event["action"]
		if isinstance(action_data, list) or action_data is None:
			# No tool action
			tool_action = ToolAction()
		else:
			# Tool action exists
			tool_action = ToolAction(
				tool=action_data.get("tool"),
				tool_input=action_data.get("tool_input"),
				tool_output=action_data.get("tool_output")
			)
		
		yield UnifiedEvent(
			user_id=user_id,
			conversationId=conversation_id,
			output=event["ai_output"],
			action=tool_action,
		)
		continue

	if last_assistant["ai_output"] is None:
		conv.append(ConversationMessage(role="assistant", content=last_assistant["ai_output"], timestamp=now_utc()))
	if last_assistant["action"]:
		conv.append(ConversationMessage(role=last_assistant["action"]['tool_name'], content=last_assistant["action"]['tool_output'], timestamp=now_utc()))

	# human or other messages can be ignored or echoed as no-op
