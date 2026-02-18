"""Gateway service main entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.application.services import JobService
from gateway.infrastructure.cache import RedisCache
from gateway.infrastructure.messaging import RabbitMQPublisher
from gateway.infrastructure.persistence import JobRepositoryImpl
from gateway.interface.routes import router as api_router
from shared.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global service instances
_cache: RedisCache | None = None
_publisher: RabbitMQPublisher | None = None
_job_service: JobService | None = None


def get_job_service() -> JobService:
    """Get or create JobService instance."""
    global _job_service
    if _job_service is None:
        settings = get_settings()
        _job_service = JobService(
            job_repository=JobRepositoryImpl(),
            message_publisher=_publisher,
            cache_client=_cache,
            cache_ttl=settings.redis_job_ttl,
        )
    return _job_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    global _cache, _publisher

    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")

    # Initialize infrastructure
    _cache = RedisCache(url=settings.redis_url)
    await _cache.connect()

    _publisher = RabbitMQPublisher(
        url=settings.rabbitmq_url,
        queue_name=settings.rabbitmq_task_queue,
    )
    await _publisher.connect()

    logger.info("Gateway service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Gateway service")
    if _cache:
        await _cache.disconnect()
    if _publisher:
        await _publisher.disconnect()
    logger.info("Gateway service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AI Platform Gateway",
    description="REST API for submitting AI processing jobs and checking their status",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Platform Gateway",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
