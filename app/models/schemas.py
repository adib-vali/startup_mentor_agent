from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from datetime import datetime


class ChatPostRequest(BaseModel):
	user_id: int
	conversation_id: int = Field(..., alias="conversationId")
	text: str

	model_config = ConfigDict(populate_by_name=True)


class TokenResponse(BaseModel):
	token: str
	expires_in: int


class ConversationMessage(BaseModel):
	role: Literal["user", "assistant", "tool", "system"]
	content: str
	timestamp: datetime


class PendingRun(BaseModel):
	token: str
	user_id: int
	conversation_id: int
	text: str
	created_at: datetime 