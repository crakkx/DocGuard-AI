from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.config import settings
from app.database import init_db

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DocGuard AI...")
    # Create uploads directory
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    # Load embedding model
    try:
        from sentence_transformers import SentenceTransformer
        app.state.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {settings.EMBEDDING_MODEL}")
    except Exception as e:
        logger.warning(f"Could not load embedding model: {e}")
        app.state.embedding_model = None
    yield
    logger.info("Shutting down DocGuard AI...")

app = FastAPI(
    title="DocGuard AI",
    description="Procurement Compliance and Audit Reviewer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import documents, cases, rules, review, policy, dashboard
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(policy.router, prefix="/api/policies", tags=["policies"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
# Case audit trail is served by cases.router (GET /api/cases/{id}/audit) — the
# former app/routers/audit.py was a dead duplicate stub of that same path and
# app/routers/compliance.py an unused leftover scaffold; both were removed.

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "DocGuard AI"}

# Mount uploads directory for file serving
uploads_path = Path(settings.UPLOAD_DIR)
if uploads_path.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
