"""API route definitions."""
from fastapi import APIRouter, Depends

from gateway.interface.controllers import JobController
from gateway.interface.controllers.job_controller import get_job_controller
from gateway.interface.schemas import (
    ErrorResponse,
    HealthResponse,
    JobStatusResponse,
    SubmitJobRequest,
    SubmitJobResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    controller = get_job_controller()
    return await controller.health_check()


@router.post(
    "/v1/jobs",
    response_model=SubmitJobResponse,
    status_code=201,
    responses={
        201: {"description": "Job created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Jobs"],
)
async def submit_job(request: SubmitJobRequest):
    """Submit a new job for AI processing.

    Creates a new job and queues it for processing by the AI Engine.
    Returns immediately with a job ID for status polling.
    """
    controller = get_job_controller()
    return await controller.submit_job(request)


@router.get(
    "/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status retrieved"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Jobs"],
)
async def get_job_status(job_id: str):
    """Get the current status of a job.

    Returns the current state of the job including:
    - Status (QUEUED, PROCESSING, COMPLETED, FAILED)
    - Result (when completed)
    - Error message (when failed)
    """
    controller = get_job_controller()
    return await controller.get_job_status(job_id)
