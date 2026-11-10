"""
backend/app/schemas/common.py
Generic schemas including global error envelopes and standard pagination wrappers.
"""
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationEnvelope(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)

