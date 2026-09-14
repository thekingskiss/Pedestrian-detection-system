from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Real deployment: start the pipeline_orchestrator background task(s)
    # here (one per active camera), and load the active YOLO model via
    # app/ml/model_registry.py. Left out of the HTTP process's lifespan in
    # this scaffold — see services/pipeline_orchestrator.py's module
    # docstring for why inference runs as a separate worker process.
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    def health_check() -> dict:
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
