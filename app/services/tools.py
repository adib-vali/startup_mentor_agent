from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
import httpx
from langchain.tools import BaseTool

from app.config import settings


class AnalysisInput(BaseModel):
	startup_description: str = Field(..., description="A clear and comprehensive description of the startup idea")
	analysis_mode: str = Field(default="advanced", description="Analysis depth, e.g., 'basic' or 'advanced'")
	include_external_research: bool = Field(default=True, description="Whether to include external research in analysis")


_DEFAULT_HEADERS = {"Content-Type": "application/json"}


class ExternalAnalysisTool(BaseTool):
	name = "external_market_product_founder_analysis"
	description = (
		"Use this tool when you have a sufficiently detailed startup description and want a structured analysis. "
		"Provide: startup_description, analysis_mode, include_external_research."
	)
	args_schema: type[BaseModel] = AnalysisInput

	def _run(self, startup_description: str, analysis_mode: str = "advanced", include_external_research: bool = True) -> dict:  # type: ignore[override]
		payload = {
			"startup_description": startup_description,
			"analysis_mode": analysis_mode,
			"include_external_research": include_external_research,
		}
		with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
			resp = client.post(settings.ANALYSIS_API_URL, json=payload, headers=_DEFAULT_HEADERS)
			resp.raise_for_status()
			return resp.json()

	async def _arun(self, startup_description: str, analysis_mode: str = "advanced", include_external_research: bool = True) -> dict:  # type: ignore[override]
		payload = {
			"startup_description": startup_description,
			"analysis_mode": analysis_mode,
			"include_external_research": include_external_research,
		}
		async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
			resp = await client.post(settings.ANALYSIS_API_URL, json=payload, headers=_DEFAULT_HEADERS)
			resp.raise_for_status()
			return resp.json()


def build_tools() -> list[BaseTool]:
	return [ExternalAnalysisTool()] 