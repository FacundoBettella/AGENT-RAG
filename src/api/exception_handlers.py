from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.exceptions import ContentBlockedError


# Starlette's add_exception_handler types handlers as (Request, Exception),
# so each handler takes a plain Exception and narrows it with cast(): the
# framework only dispatches the registered exception class to each handler.


async def content_blocked_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": cast(ContentBlockedError, exc).reason})


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(HTTPException, exc)
    return JSONResponse(status_code=http_exc.status_code, content={"error": http_exc.detail})


async def validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": str(exc)})


async def generic_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})


def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ContentBlockedError, content_blocked_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, generic_handler)
