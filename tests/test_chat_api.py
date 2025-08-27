import json
import time
from typing import List, Dict

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
	return TestClient(app)


def _read_sse_events(resp) -> List[Dict]:
	events: List[Dict] = []
	for line in resp.iter_lines():
		if not line:
			continue
		if line.startswith("data: "):
			data = line[len("data: "):]
			try:
				events.append(json.loads(data))
			except json.JSONDecodeError:
				continue
		# Stop after collecting a few events to avoid long waits
		if len(events) >= 3:
			break
	return events


def test_post_message_returns_token(client: TestClient):
	payload = {"user_id": 1, "conversationId": 123, "text": "سلام"}
	r = client.post("/chat/message", json=payload)
	assert r.status_code == 200
	data = r.json()
	assert "token" in data and isinstance(data["token"], str)
	assert "expires_in" in data and isinstance(data["expires_in"], int)


def test_stream_with_invalid_token_404(client: TestClient):
	r = client.get("/chat/stream", params={"token": "invalid"})
	assert r.status_code == 404


def test_stream_without_api_key_streams_error(client: TestClient):
	# Ensure missing API key during this test
	settings.OPENAI_API_KEY = ""
	payload = {"user_id": 2, "conversationId": 456, "text": "Test idea"}
	token = client.post("/chat/message", json=payload).json()["token"]

	with client.stream("GET", "/chat/stream", params={"token": token}) as resp:
		assert resp.status_code == 200
		events = _read_sse_events(resp)
		# Expect started -> error -> done
		types = [e.get("type") for e in events]
		assert "error" in types
		err = next((e for e in events if e.get("type") == "error"), None)
		assert err is not None and "LLM not configured" in (err.get("error") or "") 