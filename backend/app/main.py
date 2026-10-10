from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.conjugation import router as conjugation_router
from app.api.errors import ApiProblem
from app.api.health import router as health_router
from app.api.verb_search import router as verb_search_router

app = FastAPI(
    title="COQ API",
    description=(
        "API de COQ. La consulta de conjugación solo expone formas de verbos, "
        "patrones y construcciones aprobados en el catálogo de producción."
    ),
    version="0.2.0",
)

# Production origins must be set from deployment configuration before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(ApiProblem)
async def api_problem_handler(_: Request, exc: ApiProblem) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response.model_dump(mode="json"),
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(verb_search_router, prefix="/api/v1")
app.include_router(conjugation_router, prefix="/api/v1")
