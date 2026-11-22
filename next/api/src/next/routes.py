"""Endpoints of the API and the responses for its errors."""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from next.data import DataError, OrderRepository, OrdersData
from next.settings import Settings
from next.utils import list_route_paths

router = APIRouter()


def get_repository(request: Request) -> OrderRepository:
    return request.app.state.repository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


Repository = Annotated[OrderRepository, Depends(get_repository)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/")
def home(settings: AppSettings) -> dict:
    return {"service": settings.service_name, "routes": list_route_paths(router)}


@router.get("/health")
def health(request: Request, repository: Repository) -> dict:
    data = repository.read()
    request.state.data_version = data.data_version

    return {"status": "ok", "data_version": data.data_version}


@router.get("/orders")
def orders(request: Request, repository: Repository) -> OrdersData:
    data = repository.read()
    request.state.data_version = data.data_version
    
    return data


def data_error_handler(request: Request, error: DataError) -> JSONResponse:
    return JSONResponse({"status": "data_error"}, status_code=503)


def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    messages = {404: "Route not found", 405: "Method not allowed"}
    message = messages.get(error.status_code, str(error.detail))
    return JSONResponse({"error": message}, status_code=error.status_code)


def register_routes(app: FastAPI) -> None:
    """Attach the endpoints and the error responses to the app."""
    app.include_router(router)
    app.add_exception_handler(DataError, data_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
