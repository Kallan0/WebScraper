from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(min_length=1, max_length=2048)


class SummaryData(BaseModel):
    url: str
    title: str | None
    content_type: str
    characters_processed: int
    summary: str
    truncated: bool = False


class SummarizeResponse(BaseModel):
    success: Literal[True] = True
    data: SummaryData


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: str
