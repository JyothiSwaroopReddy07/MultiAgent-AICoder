"""
LLM Usage Tracker - Monitors API calls and token usage
"""
from typing import Dict, Optional
from datetime import datetime
import structlog
from models.schemas import LLMUsage

logger = structlog.get_logger()


class LLMTracker:
    """Tracks LLM API calls and token usage"""

    # Pricing per 1K tokens (as of 2024 - update as needed)
    PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
    }

    def __init__(self):
        self.usage_history: list[LLMUsage] = []
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    def track_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_metadata: Optional[Dict] = None
    ) -> LLMUsage:
        """
        Track a single LLM API call

        Args:
            model: Model name used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            response_metadata: Additional metadata from the API response

        Returns:
            LLMUsage object with usage details
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        usage = LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost
        )

        self.usage_history.append(usage)
        self.total_calls += 1
        self.total_tokens += total_tokens
        self.total_cost += cost

        logger.info(
            "llm_usage_tracked",
            model=model,
            tokens=total_tokens,
            cost=cost,
            total_calls=self.total_calls
        )

        return usage

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost based on model and token usage"""
        # Normalize model name
        model_key = model.lower()
        for key in self.PRICING.keys():
            if key in model_key:
                model_key = key
                break

        if model_key not in self.PRICING:
            logger.warning(f"Unknown model for pricing: {model}, defaulting to gpt-3.5-turbo")
            model_key = "gpt-3.5-turbo"

        pricing = self.PRICING[model_key]
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]

        return round(prompt_cost + completion_cost, 6)

    def get_summary(self) -> Dict:
        """Get summary of all LLM usage"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "average_tokens_per_call": round(self.total_tokens / max(self.total_calls, 1), 2),
            "usage_by_model": self._usage_by_model()
        }

    def _usage_by_model(self) -> Dict[str, Dict]:
        """Group usage statistics by model"""
        by_model = {}
        for usage in self.usage_history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            by_model[usage.model]["calls"] += 1
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["cost"] += usage.cost or 0.0

        # Round costs
        for model in by_model:
            by_model[model]["cost"] = round(by_model[model]["cost"], 4)

        return by_model

    def reset(self):
        """Reset all tracking data"""
        self.usage_history.clear()
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        logger.info("llm_tracker_reset")


# Global tracker instance
tracker = LLMTracker()
