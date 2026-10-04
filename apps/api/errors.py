"""Tianze API 错误模型：统一 TianzeError → HTTP 错误映射。"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from tianze.sdk import TianzeError


def tianze_error_handler(request: Request, exc: TianzeError) -> JSONResponse:
    status_map = {
        "INVALID_BIRTH_INFO": 422,
        "UNSUPPORTED_CONVENTION": 400,
        "KNOWLEDGE_DATA_ERROR": 500,
        "ANALYSIS_UNAVAILABLE": 422,
    }
    status = status_map.get(exc.code, 500)
    return JSONResponse(
        status_code=status,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
