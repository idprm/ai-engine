"""LLM Selector domain service."""
from ai_engine.domain.entities import LLMConfig


class LLMSelector:
    """Domain service for selecting appropriate LLM configurations.

    Contains business logic for choosing the right LLM based on
    requirements like cost, speed, or capability.
    """

    @staticmethod
    def select_for_task(
        configs: list[LLMConfig],
        prefer_speed: bool = False,
        prefer_quality: bool = False,
    ) -> LLMConfig | None:
        """Select the best LLM config for a given task.

        Args:
            configs: Available LLM configurations.
            prefer_speed: Prioritize faster models.
            prefer_quality: Prioritize higher quality models.

        Returns:
            The selected LLMConfig or None if no active configs.
        """
        active_configs = [c for c in configs if c.is_active]
        if not active_configs:
            return None

        if prefer_quality:
            # Prefer larger models (opus, gpt-4)
            quality_order = ["opus", "gpt-4", "sonnet", "gpt-3.5"]
            for pattern in quality_order:
                for config in active_configs:
                    if pattern in str(config.model_name).lower():
                        return config

        if prefer_speed:
            # Prefer smaller, faster models
            speed_order = ["gpt-3.5", "sonnet", "gpt-4", "opus"]
            for pattern in speed_order:
                for config in active_configs:
                    if pattern in str(config.model_name).lower():
                        return config

        # Default: return first active config
        return active_configs[0]
