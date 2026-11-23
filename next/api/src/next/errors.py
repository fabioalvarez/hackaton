"""Errors of the API and their responses."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from next.observability import logger


class DataError(Exception):
    """The data file is missing, unreadable or invalid."""


def data_error_handler(request: Request, error: DataError) -> JSONResponse:
    # The cause (missing file, bad JSON, invalid schema) only goes to the log, not to the client.
    fields = {
        "instance": request.app.state.settings.instance_id,
        "path": request.url.path,
        "cause": str(error),
    }
    logger.error("data error", extra={"fields": fields})

    return JSONResponse({"status": "data_error"}, status_code=503)


def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    messages = {
        404: "Route not found",
        405: "Method not allowed",
    }

    message = messages.get(
        error.status_code,
        str(error.detail),
    )
    
    return JSONResponse(
        {"error": message},
        status_code=error.status_code,
        )
