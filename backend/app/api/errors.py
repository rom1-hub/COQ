"""Stable API errors shared by COQ HTTP endpoints."""
from __future__ import annotations

from app.api.contracts import ApiErrorCode, ApiErrorResponse


class ApiProblem(Exception):
    def __init__(
        self,
        status_code: int,
        code: ApiErrorCode,
        message: str,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = ApiErrorResponse(
            code=code,
            message=message,
            details=details or {},
        )
