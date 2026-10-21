"""api/errors.py: every error leaves the API in the same shape: {code, message, field?, errors?}."""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.checks import InvalidReadings


class ApiError(HTTPException):
    """Raise ApiError(404, "unknown_crop", "No crop called 'x'.") from any route."""

    def __init__(self, status: int, code: str, message: str, field: str | None = None):
        super().__init__(status_code=status, detail={"code": code, "message": message, "field": field})


def _body(code: str, message: str, field: str | None = None, errors: list | None = None) -> dict:
    return {"code": code, "message": message, "field": field, "errors": errors}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_body(**exc.detail))

    @app.exception_handler(InvalidReadings)
    async def _invalid(_: Request, exc: InvalidReadings):
        errors = [{"field": f, "message": m} for f, m in exc.errors]
        return JSONResponse(status_code=422, content=_body("invalid_readings", "Some readings are not valid.", errors[0]["field"], errors))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = []
        for e in exc.errors():
            loc = [str(x) for x in e["loc"] if x not in ("body", "query", "path")]
            errors.append({"field": ".".join(loc) or None, "message": e["msg"]})
        first = errors[0] if errors else {"field": None}
        return JSONResponse(status_code=422, content=_body("validation_error", "The request is not valid.", first["field"], errors))

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=_body("http_error", detail))

    @app.middleware("http")
    async def _unhandled(request: Request, call_next):
        """
        Any other crash becomes a normal 500 in the one error shape. Without this the exception escaped past the CORS layer, so the
        browser saw an answer with no Access-Control-Allow-Origin and reported a CORS error instead of the real problem.
        The details go to the server log, never to the client.
        """
        try:
            return await call_next(request)
        except Exception:
            logging.getLogger("uvicorn.error").exception("unhandled error in %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content=_body("server_error", "Something went wrong on the server."))
