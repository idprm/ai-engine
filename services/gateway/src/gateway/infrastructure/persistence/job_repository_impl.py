"""Job repository implementation using SQLAlchemy."""
import logging

from gateway.domain.entities import Job
from gateway.domain.repositories import JobRepository
from gateway.domain.value_objects import JobId
from gateway.infrastructure.persistence.database import get_db_session
from gateway.infrastructure.persistence.models import JobModel

logger = logging.getLogger(__name__)


class JobRepositoryImpl(JobRepository):
    """SQLAlchemy implementation of JobRepository.

    Note: Primary persistence is Redis cache. This repository
    provides optional database persistence for audit/history.
    """

    async def get_by_id(self, job_id: JobId) -> Job | None:
        """Retrieve a job by ID from the database."""
        async with get_db_session() as session:
            model = await session.get(JobModel, str(job_id))
            if not model:
                return None
            return self._to_entity(model)

    async def save(self, job: Job) -> Job:
        """Persist a job to the database."""
        async with get_db_session() as session:
            model = await session.get(JobModel, str(job.id))
            if model:
                # Update existing
                model.status = job.status.value
                model.result = job.result
                model.error = job.error
            else:
                # Create new
                model = JobModel(
                    id=str(job.id),
                    prompt=str(job.prompt),
                    config_name=job.config_name,
                    template_name=job.template_name,
                    status=job.status.value,
                    result=job.result,
                    error=job.error,
                )
                session.add(model)
            return job

    async def delete(self, job_id: JobId) -> bool:
        """Delete a job from the database."""
        async with get_db_session() as session:
            model = await session.get(JobModel, str(job_id))
            if model:
                await session.delete(model)
                return True
            return False

    async def exists(self, job_id: JobId) -> bool:
        """Check if a job exists in the database."""
        async with get_db_session() as session:
            model = await session.get(JobModel, str(job_id))
            return model is not None

    def _to_entity(self, model: JobModel) -> Job:
        """Convert ORM model to domain entity."""
        from gateway.domain.value_objects import Prompt

        return Job(
            _id=JobId.from_string(model.id),
            _prompt=Prompt(content=model.prompt),
            _config_name=model.config_name,
            _template_name=model.template_name,
            _status=model.status,
            _result=model.result,
            _error=model.error,
            _created_at=model.created_at,
            _updated_at=model.updated_at,
            _events=[],  # Don't re-emit events on load
        )
