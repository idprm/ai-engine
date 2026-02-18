"""Processing application service."""
import json
import logging
from typing import Protocol

from ai_engine.application.dto import ProcessingRequest, ProcessingResult
from ai_engine.domain.entities import LLMConfig, PromptTemplate
from ai_engine.domain.repositories import LLMConfigRepository, PromptTemplateRepository
from shared.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class LLMRunner(Protocol):
    """Protocol for LLM execution (implemented in infrastructure)."""

    async def run(self, config: LLMConfig, system_prompt: str, user_prompt: str) -> tuple[str, int]:
        """Run LLM with given configuration and prompts.

        Args:
            config: LLM configuration.
            system_prompt: System prompt text.
            user_prompt: User prompt text.

        Returns:
            Tuple of (response text, tokens used).
        """
        ...


class CacheClient(Protocol):
    """Protocol for cache operations."""

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache."""
        ...


class ProcessingService:
    """Application service for processing AI jobs.

    Orchestrates the complete processing pipeline:
    1. Load LLM config and prompt template
    2. Execute LLM with LangGraph
    3. Update job status in cache
    """

    def __init__(
        self,
        llm_config_repository: LLMConfigRepository,
        prompt_template_repository: PromptTemplateRepository,
        llm_runner: LLMRunner,
        cache_client: CacheClient,
        cache_ttl: int = 3600,
    ):
        self._llm_config_repo = llm_config_repository
        self._prompt_template_repo = prompt_template_repository
        self._llm_runner = llm_runner
        self._cache_client = cache_client
        self._cache_ttl = cache_ttl

    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """Process a job request.

        Args:
            request: The processing request.

        Returns:
            ProcessingResult with outcome.
        """
        logger.info(f"Processing job: {request.job_id}")

        try:
            # Update status to PROCESSING
            await self._update_status(request.job_id, "PROCESSING")

            # Load configuration
            config = await self._llm_config_repo.get_by_name(request.config_name)
            if not config:
                raise NotFoundException("LLMConfig", request.config_name)

            # Load prompt template
            template = await self._prompt_template_repo.get_by_name(request.template_name)
            if not template:
                raise NotFoundException("PromptTemplate", request.template_name)

            # Execute LLM
            result, tokens = await self._llm_runner.run(
                config=config,
                system_prompt=template.content,
                user_prompt=request.prompt,
            )

            # Update status to COMPLETED
            await self._update_status(request.job_id, "COMPLETED", result=result)

            logger.info(f"Job completed: {request.job_id}, tokens: {tokens}")

            return ProcessingResult(
                job_id=request.job_id,
                status="COMPLETED",
                result=result,
                tokens_used=tokens,
            )

        except NotFoundException as e:
            error_msg = f"Configuration not found: {e.message}"
            logger.error(f"Job failed ({request.job_id}): {error_msg}")
            await self._update_status(request.job_id, "FAILED", error=error_msg)
            return ProcessingResult(
                job_id=request.job_id,
                status="FAILED",
                error=error_msg,
            )

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Job failed ({request.job_id}): {error_msg}")
            await self._update_status(request.job_id, "FAILED", error=error_msg)
            return ProcessingResult(
                job_id=request.job_id,
                status="FAILED",
                error=error_msg,
            )

    async def _update_status(
        self,
        job_id: str,
        status: str,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status in cache."""
        data = {"job_id": job_id, "status": status}
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error

        await self._cache_client.set(
            key=job_id,
            value=json.dumps(data),
            ttl=self._cache_ttl,
        )
