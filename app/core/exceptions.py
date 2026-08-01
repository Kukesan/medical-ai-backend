from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


class AppException(Exception):
    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST, code: str = "error"):
        self.message = message
        self.status_code = int(status_code)
        self.code = code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=HTTPStatus.NOT_FOUND, code="not_found")


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=HTTPStatus.UNAUTHORIZED, code="unauthorized")


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def rate_limit_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
        content={"error": {"code": "rate_limited", "message": "Too many requests"}},
    )
