import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.realtime import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.bind_loop(asyncio.get_running_loop())
    yield

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configuration CORS pour autoriser le frontend Angular
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Format d'erreur du contrat (docs/API.md) : { "message": "...", "errors": {...} }
# `detail` est conservé pour les clients FastAPI habituels.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Erreur lors du traitement de la requête."
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": message, "detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors: dict[str, list[str]] = {}
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        errors.setdefault(field or "_", []).append(err.get("msg", "Valeur invalide"))
    first = next(iter(errors.items()), None)
    message = f"Données invalides ({first[0]} : {first[1][0]})" if first else "Données invalides."
    return JSONResponse(status_code=422, content={"message": message, "errors": errors})


# Inclusion des routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Si API_V1_STR est "/api", on monte aussi "/api/v1" pour compatibilité ascendante
if settings.API_V1_STR != "/api/v1":
    app.include_router(api_router, prefix="/api/v1")

# Répertoire des uploads pour pièces jointes
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
