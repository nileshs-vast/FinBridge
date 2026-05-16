from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, dashboard, health, onboarding, reports, transactions
from app.core.config import Settings, get_settings
from app.extraction import build_provider


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.extraction_provider = build_provider(app.state.settings)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()

    app = FastAPI(
        title="FinBridge API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(transactions.router, prefix="/api")
    app.include_router(onboarding.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")

    app.state.settings = cfg

    # Serve React SPA in production. Uses a 404 exception handler (not a catch-all route)
    # so dynamically added routes (e.g. in tests) are never shadowed.
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        from fastapi.exception_handlers import http_exception_handler
        from starlette.exceptions import HTTPException as StarletteHTTPException

        @app.exception_handler(StarletteHTTPException)
        async def spa_exception_handler(request, exc: StarletteHTTPException):
            if exc.status_code == 404 and not request.url.path.startswith("/api"):
                return FileResponse(str(static_dir / "index.html"))
            return await http_exception_handler(request, exc)

    return app


app = create_app()
