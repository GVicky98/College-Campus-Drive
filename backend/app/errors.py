"""One error envelope for the whole API: {"error": {"code", "message", "details?"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("campus")


class ApiError(Exception):
    status = 400
    code = "bad_request"
    default_message = "The request could not be processed."

    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details


class BadRequest(ApiError):
    pass


class Unauthenticated(ApiError):
    status, code, default_message = 401, "unauthenticated", "Please sign in again."


class Forbidden(ApiError):
    status, code, default_message = 403, "forbidden", "You do not have permission to do this."


class NotFound(ApiError):
    status, code, default_message = 404, "not_found", "Not found."


class Conflict(ApiError):
    status, code, default_message = 409, "conflict", "This conflicts with the current state."


class ValidationFailed(ApiError):
    status, code, default_message = 422, "validation_error", "Some fields are invalid."

    def __init__(self, message: str | None = None, details: dict | None = None, field: str | None = None):
        if field and details is None:
            details = {field: [message or self.default_message]}
        super().__init__(message, details)


class RateLimited(ApiError):
    status, code, default_message = 429, "rate_limited", "Too many attempts. Please wait and try again."


class NotImplementedYet(ApiError):
    status, code, default_message = 501, "not_implemented", "This feature is not available on the server yet."


def _envelope(status: int, code: str, message: str, details: dict | None = None, headers: dict | None = None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status, headers=headers)


def pydantic_details(errors) -> dict[str, list[str]]:
    details: dict[str, list[str]] = {}
    for e in errors:
        loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
        key = ".".join(loc) or "body"
        msg = e.get("msg", "Invalid value").removeprefix("Value error, ")
        details.setdefault(key, []).append(msg)
    return details


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _envelope(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = pydantic_details(exc.errors())
        first_key = next(iter(details), "body")
        message = f"{first_key}: {details[first_key][0]}" if details else "Some fields are invalid."
        return _envelope(422, "validation_error", message, details)

    @app.exception_handler(ValidationError)
    async def _model_validation(_: Request, exc: ValidationError):
        # Raised when a service or a query model validates input itself.
        details = pydantic_details(exc.errors())
        first_key = next(iter(details), "body")
        return _envelope(422, "validation_error", f"{first_key}: {details[first_key][0]}" if details else "Invalid input.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large", 401: "unauthenticated"}
        return _envelope(exc.status_code, codes.get(exc.status_code, "bad_request"), str(exc.detail or "Request failed."))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return _envelope(500, "server_error", "The server ran into a problem. Please try again.")
