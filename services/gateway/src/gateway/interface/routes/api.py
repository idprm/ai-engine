"""API route definitions."""
from fastapi import APIRouter, Depends, Header, Request

from gateway.interface.controllers import JobController, WAController
from gateway.interface.controllers.job_controller import get_job_controller
from gateway.interface.controllers.wa_controller import get_wa_controller
from gateway.interface.schemas import (
    ErrorResponse,
    HealthResponse,
    JobStatusResponse,
    SubmitJobRequest,
    SubmitJobResponse,
    WAWebhookPayload,
    WAWebhookResponse,
    WASendMessageRequest,
    WASendMessageResponse,
)
from gateway.interface.routes.crm_routes import crm_router

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

    Creates a new job and queues it for processing by the LLM Worker.
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


# WhatsApp Webhook Routes

@router.post(
    "/v1/webhook/whatsapp",
    response_model=WAWebhookResponse,
    responses={
        200: {"description": "Webhook processed successfully"},
        401: {"model": ErrorResponse, "description": "Invalid HMAC signature"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["WhatsApp"],
)
async def handle_wa_webhook(
    request: Request,
    payload: WAWebhookPayload,
    x_webhook_hmac: str | None = Header(default=None, alias="X-Webhook-Hmac"),
):
    """Handle incoming WAHA webhook events.

    This endpoint receives webhook events from WAHA (WhatsApp HTTP API).

    The webhook receives events like:
    - message: New incoming message
    - message.any: Any message (including sent)
    - message.reaction: Message reaction
    - session.status: Session status changes

    WAHA sends HMAC signature in X-Webhook-Hmac header for verification.
    """
    controller = get_wa_controller()
    return await controller.handle_webhook(request, payload, x_webhook_hmac)


@router.post(
    "/v1/whatsapp/send",
    response_model=WASendMessageResponse,
    responses={
        200: {"description": "Message queued for sending"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["WhatsApp"],
)
async def send_wa_message(request: WASendMessageRequest):
    """Queue a WhatsApp message for sending.

    This endpoint queues a message to be sent via the Messenger service.
    The message will be delivered asynchronously.
    """
    controller = get_wa_controller()
    return await controller.send_message(request)


# Include CRM routes
router.include_router(crm_router)
