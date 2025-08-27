from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

	OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
	MODEL_NAME: str = Field(default="gpt-4o-mini", description="LLM model name")

	ANALYSIS_API_URL: str = Field(default="http://82.115.18.200/api/v1/analyze", description="External analysis API URL")

	TOKEN_TTL_SECONDS: int = Field(default=300, description="TTL for SSE tokens in seconds")
	CONVERSATION_TTL_SECONDS: int = Field(default=60 * 60 * 24, description="TTL for conversations without activity")
	PURGE_INTERVAL_SECONDS: int = Field(default=30, description="Background purge interval in seconds")


settings = Settings()  # type: ignore 