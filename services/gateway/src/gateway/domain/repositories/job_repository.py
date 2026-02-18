"""Abstract Job repository interface."""
from abc import ABC, abstractmethod

from gateway.domain.entities import Job
from gateway.domain.value_objects import JobId


class JobRepository(ABC):
    """Abstract repository interface for Job aggregate.

    This interface defines the contract for job persistence.
    Implementation details are in the infrastructure layer.
    """

    @abstractmethod
    async def get_by_id(self, job_id: JobId) -> Job | None:
        """Retrieve a job by its unique identifier.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            The Job aggregate if found, None otherwise.
        """
        pass

    @abstractmethod
    async def save(self, job: Job) -> Job:
        """Persist a job aggregate.

        Args:
            job: The job aggregate to persist.

        Returns:
            The persisted job with any updated fields.
        """
        pass

    @abstractmethod
    async def delete(self, job_id: JobId) -> bool:
        """Delete a job by its identifier.

        Args:
            job_id: The unique identifier of the job to delete.

        Returns:
            True if the job was deleted, False if not found.
        """
        pass

    @abstractmethod
    async def exists(self, job_id: JobId) -> bool:
        """Check if a job exists.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            True if the job exists, False otherwise.
        """
        pass
