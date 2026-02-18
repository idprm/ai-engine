"""Job controller handling HTTP requests."""
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status

from gateway.application.dto import JobDTO, JobStatusDTO
from gateway.application.services import JobService
from gateway.interface.schemas import (
    ErrorResponse,
    HealthResponse,
    JobStatusResponse,
    SubmitJobRequest,
    SubmitJobResponse,
)
from shared.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class JobController:
    """Controller for job-related HTTP endpoints.

    Handles request/response transformation and delegates
    business logic to the application service.
    """

    def __init__(self, job_service: JobService):
        self._job_service = job_service

    async def submit_job(self, request: SubmitJobRequest) -> SubmitJobResponse:
        """Submit a new job for processing.

        Args:
            request: Job submission request.

        Returns:
            SubmitJobResponse with job ID and initial status.

        Raises:
            HTTPException: If validation fails or processing error occurs.
        """
        try:
            dto = JobDTO(
                prompt=request.prompt,
                config_name=request.config_name,
                template_name=request.template_name,
            )
            result = await self._job_service.submit_job(dto)
            return SubmitJobResponse(
                job_id=result.job_id,
                status=result.status,
            )
        except ValidationException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": e.message, "field": e.field},
            )
        except Exception as e:
            logger.exception("Failed to submit job")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit job",
            )

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get the current status of a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            JobStatusResponse with current job state.

        Raises:
            HTTPException: If job not found or error occurs.
        """
        try:
            result = await self._job_service.get_job_status(job_id)
            return JobStatusResponse(
                job_id=result.job_id,
                status=result.status,
                result=result.result,
                error=result.error,
                created_at=result.created_at.isoformat() if result.created_at else None,
                updated_at=result.updated_at.isoformat() if result.updated_at else None,
            )
        except NotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=e.message,
            )
        except Exception as e:
            logger.exception(f"Failed to get job status: {job_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve job status",
            )

    async def health_check(self) -> HealthResponse:
        """Health check endpoint.

        Returns:
            HealthResponse indicating service health.
        """
        return HealthResponse()


# Dependency injection helper
def get_job_controller() -> JobController:
    """Factory function for JobController dependency injection."""
    from gateway.main import get_job_service
    return JobController(job_service=get_job_service())
