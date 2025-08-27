from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Dict, List, Tuple, Optional
import secrets

from app.models.schemas import ConversationMessage, PendingRun


UTC = timezone.utc


def now_utc() -> datetime:
	return datetime.now(UTC)


@dataclass
class Conversation:
	user_id: int
	conversation_id: int
	messages: List[ConversationMessage] = field(default_factory=list)
	last_activity: datetime = field(default_factory=now_utc)
	last_user_activity: datetime = field(default_factory=now_utc)

	def append(self, message: ConversationMessage) -> None:
		self.messages.append(message)
		self.last_activity = now_utc()
		if message.role == "user":
			self.last_user_activity = self.last_activity


class ConversationStore:
	def __init__(self) -> None:
		self._lock = RLock()
		self._data: Dict[Tuple[int, int], Conversation] = {}

	def get_or_create(self, user_id: int, conversation_id: int) -> Conversation:
		key = (user_id, conversation_id)
		with self._lock:
			conv = self._data.get(key)
			if conv is None:
				conv = Conversation(user_id=user_id, conversation_id=conversation_id)
				self._data[key] = conv
			return conv

	def purge_expired(self, ttl_seconds: int) -> None:
		cutoff = now_utc() - timedelta(seconds=ttl_seconds)
		with self._lock:
			to_delete = [key for key, conv in self._data.items() if conv.last_user_activity < cutoff]
			for key in to_delete:
				self._data.pop(key, None)


class TokenStore:
	def __init__(self) -> None:
		self._lock = RLock()
		self._data: Dict[str, PendingRun] = {}

	def issue_token(self, user_id: int, conversation_id: int, text: str) -> PendingRun:
		with self._lock:
			token = secrets.token_urlsafe(24)
			pending = PendingRun(token=token, user_id=user_id, conversation_id=conversation_id, text=text, created_at=now_utc())
			self._data[token] = pending
			return pending

	def pop(self, token: str) -> Optional[PendingRun]:
		with self._lock:
			return self._data.pop(token, None)

	def get(self, token: str) -> Optional[PendingRun]:
		with self._lock:
			return self._data.get(token)

	def purge_expired(self, ttl_seconds: int) -> None:
		cutoff = now_utc() - timedelta(seconds=ttl_seconds)
		with self._lock:
			to_delete = [k for k, v in self._data.items() if v.created_at < cutoff]
			for k in to_delete:
				self._data.pop(k, None)


conversation_store = ConversationStore()
token_store = TokenStore() 