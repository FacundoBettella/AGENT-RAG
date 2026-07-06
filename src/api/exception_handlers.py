from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.exceptions import ContentBlockedError


async def content_blocked_handler(_request: Request, exc: ContentBlockedError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.reason})


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": str(exc)})


async def generic_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})


def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ContentBlockedError, content_blocked_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, generic_handler)
