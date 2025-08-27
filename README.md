# Startup Mentor Agent

FastAPI + LangGraph ReAct agent that chats with founders about their startup idea, asks clarifying questions, and (when enough info is available) calls an external HTTP analysis tool to deliver a structured analysis. Provides a POST endpoint to enqueue messages and an SSE endpoint to stream agent events.

## Requirements
- Python 3.11+
- An OpenAI API key (set `OPENAI_API_KEY`)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in project root:
```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini
ANALYSIS_API_URL=http://82.115.18.200/api/v1/analyze
TOKEN_TTL_SECONDS=300
CONVERSATION_TTL_SECONDS=86400
PURGE_INTERVAL_SECONDS=30
```

Run server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## API

- POST `/chat/message` → returns token
  - Request body:
    ```json
    {
      "user_id": 304,
      "conversationId": 2189,
      "text": "سلام"
    }
    ```
  - Response:
    ```json
    { "token": "<token>", "expires_in": 300 }
    ```

- GET `/chat/stream?token=<token>` → SSE stream of agent events
  - Events: `started`, repeated `message` items, then `done` (or `error`)
  - Each event data is JSON with fields `{ type, role?, content?, error? }`

## Behavior
- Agent keeps conversation history in memory and asks targeted questions if the idea is incomplete.
- When sufficient details exist, the agent uses the external analysis tool at `http://82.115.18.200/api/v1/analyze` with payload:
  ```json
  {
    "startup_description": "...",
    "analysis_mode": "advanced",
    "include_external_research": true
  }
  ```
- Conversations with no user activity for 24h are purged by a background task.
- SSE tokens expire after `TOKEN_TTL_SECONDS`.

## Notes
- This project uses in-memory stores; for production, replace with a persistent store (e.g., Redis) and a robust scheduler.
- The agent prompt is in `app/services/agent.py`. Tool implementation is in `app/services/tools.py`.