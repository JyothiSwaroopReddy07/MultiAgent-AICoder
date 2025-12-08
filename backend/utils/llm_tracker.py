# Bala Aparna - 29485442

"""
LLM Usage Tracker - Monitors API calls and token usage
"""
from typing import Dict, Optional
from datetime import datetime
from contextvars import ContextVar
import structlog
from models.schemas import LLMUsage

logger = structlog.get_logger()

# Context variable to track which agent is making the current LLM call
current_agent: ContextVar[Optional[str]] = ContextVar('current_agent', default=None)


class LLMTracker:
    """Tracks LLM API calls, token usage, and calculates costs per agent"""

    # Pricing per 1K tokens (as of 2024 - update these rates as API pricing changes)
    PRICING = {
        "gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
        "gemini-1.5-pro": {"prompt": 0.00125, "completion": 0.005},
        "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
        "gemini-2.5-pro": {"prompt": 0.0035, "completion": 0.0105},
        "gemini-2.5-flash": {"prompt": 0.00035, "completion": 0.00105},
        "gemini-2.0-flash": {"prompt": 0.0001, "completion": 0.0003},
        "gemini-ultra": {"prompt": 0.0125, "completion": 0.0375},
    }

    def __init__(self):
        self.usage_history: list[Dict] = []  # Store dict with agent info
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.usage_by_agent: Dict[str, Dict] = {}  # Track usage by agent

    def track_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_metadata: Optional[Dict] = None,
        agent: Optional[str] = None
    ) -> LLMUsage:
        """
        Track a single LLM API call

        Args:
            model: Model name used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            response_metadata: Additional metadata from the API response
            agent: Name of the agent making the call (optional)

        Returns:
            LLMUsage object with usage details
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        # Get agent from context if not provided
        if agent is None:
            agent = current_agent.get() or "unknown"

        usage = LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost
        )

        # Store with agent info
        usage_entry = {
            "usage": usage,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.usage_history.append(usage_entry)

        # Update agent-specific tracking
        if agent not in self.usage_by_agent:
            self.usage_by_agent[agent] = {
                "calls": 0,
                "tokens": 0,
                "cost": 0.0,
                "models": {}
            }
        
        self.usage_by_agent[agent]["calls"] += 1
        self.usage_by_agent[agent]["tokens"] += total_tokens
        self.usage_by_agent[agent]["cost"] += cost
        
        # Track by model within agent
        if model not in self.usage_by_agent[agent]["models"]:
            self.usage_by_agent[agent]["models"][model] = {
                "calls": 0,
                "tokens": 0,
                "cost": 0.0
            }
        self.usage_by_agent[agent]["models"][model]["calls"] += 1
        self.usage_by_agent[agent]["models"][model]["tokens"] += total_tokens
        self.usage_by_agent[agent]["models"][model]["cost"] += cost

        # Update totals
        self.total_calls += 1
        self.total_tokens += total_tokens
        self.total_cost += cost

        logger.info(
            "llm_usage_tracked",
            model=model,
            tokens=total_tokens,
            cost=cost,
            agent=agent,
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
            logger.warning(f"Unknown model for pricing: {model}, defaulting to gemini-pro")
            model_key = "gemini-pro"

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
            "usage_by_model": self._usage_by_model(),
            "usage_by_agent": self._get_usage_by_agent()
        }

    def _usage_by_model(self) -> Dict[str, Dict]:
        """Group usage statistics by model"""
        by_model = {}
        for entry in self.usage_history:
            usage = entry["usage"]
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

    def _get_usage_by_agent(self) -> Dict[str, Dict]:
        """Get usage statistics grouped by agent"""
        result = {}
        for agent, stats in self.usage_by_agent.items():
            result[agent] = {
                "calls": stats["calls"],
                "tokens": stats["tokens"],
                "cost": round(stats["cost"], 4),
                "models": {
                    model: {
                        "calls": model_stats["calls"],
                        "tokens": model_stats["tokens"],
                        "cost": round(model_stats["cost"], 4)
                    }
                    for model, model_stats in stats["models"].items()
                }
            }
        return result

    def reset(self):
        """Reset all tracking data"""
        self.usage_history.clear()
        self.usage_by_agent.clear()
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        logger.info("llm_tracker_reset")

    def set_current_agent(self, agent: str):
        """Set the current agent context for tracking"""
        current_agent.set(agent)

    def clear_current_agent(self):
        """Clear the current agent context"""
        current_agent.set(None)


# Global tracker instance
tracker = LLMTracker()
