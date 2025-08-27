from fastapi import FastAPI
from contextlib import asynccontextmanager, suppress
import asyncio

from app.config import settings
from app.routers.chat import router as chat_router
from app.services.stores import conversation_store, token_store


@asynccontextmanager
async def lifespan(app: FastAPI):
	purge_task = asyncio.create_task(_purge_loop())
	try:
		yield
	finally:
		purge_task.cancel()
		with suppress(asyncio.CancelledError):
			await purge_task


async def _purge_loop() -> None:
	while True:
		conversation_store.purge_expired(settings.CONVERSATION_TTL_SECONDS)
		token_store.purge_expired(settings.TOKEN_TTL_SECONDS)
		await asyncio.sleep(settings.PURGE_INTERVAL_SECONDS)


app = FastAPI(title="Startup Mentor Agent", version="0.1.0", lifespan=lifespan)

app.include_router(chat_router, prefix="/chat", tags=["chat"]) 