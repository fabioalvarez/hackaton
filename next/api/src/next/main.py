"""FastAPI app: wiring of the app (middlewares, repository, routes)."""

import uvicorn
from fastapi import FastAPI

from next.data import OrderRepository
from next.observability import (
    InstanceHeaderMiddleware,
    RequestLogMiddleware,
    configure_logging,
)
from next.routes import register_routes
from next.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    # Interactive docs are off: the service only exposes what the demo needs.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    # The last middleware added is the outermost one.
    app.add_middleware(InstanceHeaderMiddleware, instance_id=settings.instance_id)
    app.add_middleware(RequestLogMiddleware, instance_id=settings.instance_id)

    app.state.repository = OrderRepository(settings.data_path)
    register_routes(app)

    return app


if __name__ == "__main__":
    settings = Settings()

    configure_logging(settings.log_level)

    app = create_app(settings)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_config=None,
    )
