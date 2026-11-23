"""Endpoints of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException

from next.data import OrderRepository, OrdersResponse
from next.errors import DataError, data_error_handler, http_error_handler
from next.pages import render
from next.settings import Settings

router = APIRouter()

VERSION_HEADER = "X-Data-Version"   # the version of the data that answered, in the response


def get_repository(request: Request) -> OrderRepository:
    return request.app.state.repository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


Repository = Annotated[OrderRepository, Depends(get_repository)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def wants_html(request: Request) -> bool:
    """A browser asks for HTML; programs (curl, the balancer, the tests) get the JSON."""
    return "text/html" in request.headers.get("accept", "")


def page(name: str, settings: Settings) -> HTMLResponse:
    return HTMLResponse(render(name, settings.service_name, settings.instance_id), headers={"Vary": "Accept"})


@router.get("/", response_class=HTMLResponse)
def home(settings: AppSettings) -> HTMLResponse:
    return page("home", settings)


@router.get("/health")
def health(request: Request, response: Response, repository: Repository, settings: AppSettings):
    if wants_html(request):
        return page("health", settings)

    data = repository.read()
    response.headers["Vary"] = "Accept"
    response.headers[VERSION_HEADER] = data.data_version

    return {"status": "ok"}


@router.get("/orders", response_model=OrdersResponse)
def orders(request: Request, response: Response, repository: Repository, settings: AppSettings):
    if wants_html(request):
        return page("orders", settings)

    data = repository.read()
    response.headers["Vary"] = "Accept"
    response.headers[VERSION_HEADER] = data.data_version

    return OrdersResponse(orders=data.orders)


def register_routes(app: FastAPI) -> None:
    """Attach the endpoints and the error responses to the app."""
    app.include_router(router)
    app.add_exception_handler(DataError, data_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
