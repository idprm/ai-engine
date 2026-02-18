"""Application service for job operations."""
import json
import logging
from typing import Protocol

from gateway.application.dto import JobDTO, JobStatusDTO
from gateway.domain.entities import Job
from gateway.domain.repositories import JobRepository
from gateway.domain.value_objects import JobId, Prompt
from shared.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class MessagePublisher(Protocol):
    """Protocol for message publishing (implemented in infrastructure)."""

    async def publish_task(self, job_id: str, message: dict) -> None:
        """Publish a task message to the message queue."""
        ...


class CacheClient(Protocol):
    """Protocol for cache operations (implemented in infrastructure)."""

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...


class JobService:
    """Application service orchestrating job operations.

    This service coordinates between domain objects, repositories,
    and infrastructure services without containing business logic.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        message_publisher: MessagePublisher,
        cache_client: CacheClient,
        cache_ttl: int = 3600,
    ):
        self._job_repository = job_repository
        self._message_publisher = message_publisher
        self._cache_client = cache_client
        self._cache_ttl = cache_ttl

    async def submit_job(self, dto: JobDTO) -> JobStatusDTO:
        """Submit a new job for processing.

        Args:
            dto: Job creation data.

        Returns:
            JobStatusDTO with the initial job status.

        Raises:
            ValidationException: If the job data is invalid.
        """
        # Create domain objects
        try:
            prompt = Prompt(content=dto.prompt)
        except ValueError as e:
            raise ValidationException(str(e), field="prompt")

        # Create job aggregate
        job = Job.create(
            prompt=prompt,
            config_name=dto.config_name,
            template_name=dto.template_name,
        )

        # Persist job state to cache
        await self._cache_client.set(
            key=str(job.id),
            value=json.dumps(job.to_dict()),
            ttl=self._cache_ttl,
        )

        # Publish task message for processing
        await self._message_publisher.publish_task(
            job_id=str(job.id),
            message={
                "job_id": str(job.id),
                "prompt": str(job.prompt),
                "config_name": job.config_name,
                "template_name": job.template_name,
            },
        )

        logger.info(f"Job submitted: {job.id}")

        return JobStatusDTO(
            job_id=str(job.id),
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    async def get_job_status(self, job_id: str) -> JobStatusDTO:
        """Get the current status of a job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            JobStatusDTO with current job status.

        Raises:
            NotFoundException: If the job doesn't exist.
        """
        # Get from cache
        cached_data = await self._cache_client.get(job_id)

        if not cached_data:
            raise NotFoundException("Job", job_id)

        try:
            data = json.loads(cached_data)
            return JobStatusDTO.from_dict(data)
        except json.JSONDecodeError:
            raise NotFoundException("Job", job_id)

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status (called by other services).

        Args:
            job_id: The unique identifier of the job.
            status: The new status.
            result: Optional result (for COMPLETED status).
            error: Optional error message (for FAILED status).
        """
        # Get current job data
        cached_data = await self._cache_client.get(job_id)
        if not cached_data:
            logger.warning(f"Attempted to update non-existent job: {job_id}")
            return

        data = json.loads(cached_data)
        data["status"] = status
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error

        await self._cache_client.set(
            key=job_id,
            value=json.dumps(data),
            ttl=self._cache_ttl,
        )

        logger.info(f"Job {job_id} updated to {status}")
