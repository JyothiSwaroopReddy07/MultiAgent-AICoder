"""
LLM Usage Tracker - Monitors API calls and token usage by agent
Enhanced for Multi-Agent System with MCP Integration
"""
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import structlog
from models.schemas import LLMUsage

logger = structlog.get_logger()


@dataclass
class AgentUsage:
    """Track usage for a single agent"""
    agent_name: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    last_call: Optional[datetime] = None


class LLMTracker:
    """Tracks LLM API calls and token usage by agent"""

    PRICING = {
        "gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
        "gemini-1.5-pro": {"prompt": 0.00125, "completion": 0.005},
        "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
        "gemini-2.5-pro": {"prompt": 0.0035, "completion": 0.0105},
        "gemini-2.5-flash": {"prompt": 0.00035, "completion": 0.00105},
        "gemini-2.0-flash": {"prompt": 0.0001, "completion": 0.0003},
        "gemini-ultra": {"prompt": 0.0125, "completion": 0.0375},
    }

    AGENT_DISPLAY_NAMES = {
        "FeaturePlannerAgent": "Feature Planner",
        "ArchitectAgent": "Architect",
        "FilePlannerAgent": "File Planner",
        "CodeGeneratorAgent": "Code Generator",
        "CodeReviewerAgent": "Code Reviewer",
        "IntegrationValidatorAgent": "Validator",
        "TestingAgent": "Testing",
        "TestGeneratorAgent": "Test Generator",
        "ExecutionAgent": "Execution",
        "unknown": "Unknown Agent"
    }

    def __init__(self):
        self.usage_history: list[LLMUsage] = []
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.by_agent: Dict[str, AgentUsage] = {}
        self.session_start = datetime.utcnow()

    def track_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_metadata: Optional[Dict] = None,
        agent_name: Optional[str] = None
    ) -> LLMUsage:
        """
        Track a single LLM API call

        Args:
            model: Model name used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            response_metadata: Additional metadata from the API response
            agent_name: Name of the agent making the call

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

        agent = agent_name or "unknown"
        if agent not in self.by_agent:
            self.by_agent[agent] = AgentUsage(agent_name=agent)
        
        self.by_agent[agent].calls += 1
        self.by_agent[agent].prompt_tokens += prompt_tokens
        self.by_agent[agent].completion_tokens += completion_tokens
        self.by_agent[agent].total_tokens += total_tokens
        self.by_agent[agent].cost += cost
        self.by_agent[agent].last_call = datetime.utcnow()

        logger.info(
            "llm_usage_tracked",
            model=model,
            tokens=total_tokens,
            cost=cost,
            total_calls=self.total_calls,
            agent=agent
        )

        return usage

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost based on model and token usage"""
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
        """Get comprehensive summary of all LLM usage"""
        session_duration = (datetime.utcnow() - self.session_start).total_seconds()
        
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": sum(u.prompt_tokens for u in self.usage_history),
            "total_completion_tokens": sum(u.completion_tokens for u in self.usage_history),
            "total_cost": round(self.total_cost, 4),
            "average_tokens_per_call": round(self.total_tokens / max(self.total_calls, 1), 2),
            "session_duration_seconds": round(session_duration, 2),
            "calls_per_minute": round((self.total_calls / max(session_duration, 1)) * 60, 2),
            "usage_by_model": self._usage_by_model(),
            "usage_by_agent": self._usage_by_agent()
        }

    def _usage_by_model(self) -> Dict[str, Dict]:
        """Group usage statistics by model"""
        by_model = {}
        for usage in self.usage_history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "calls": 0,
                    "tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0
                }
            by_model[usage.model]["calls"] += 1
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["prompt_tokens"] += usage.prompt_tokens
            by_model[usage.model]["completion_tokens"] += usage.completion_tokens
            by_model[usage.model]["cost"] += usage.cost or 0.0

        for model in by_model:
            by_model[model]["cost"] = round(by_model[model]["cost"], 4)

        return by_model

    def _usage_by_agent(self) -> Dict[str, Dict]:
        """Get usage breakdown by agent with display names"""
        result = {}
        
        for agent_name, agent_usage in self.by_agent.items():
            display_name = self.AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
            result[display_name] = {
                "agent_id": agent_name,
                "calls": agent_usage.calls,
                "tokens": agent_usage.total_tokens,
                "prompt_tokens": agent_usage.prompt_tokens,
                "completion_tokens": agent_usage.completion_tokens,
                "cost": round(agent_usage.cost, 4),
                "last_call": agent_usage.last_call.isoformat() if agent_usage.last_call else None,
                "percentage_of_total": round((agent_usage.calls / max(self.total_calls, 1)) * 100, 1)
            }
        
        return result

    def get_agent_stats(self, agent_name: str) -> Optional[Dict]:
        """Get usage stats for a specific agent"""
        if agent_name not in self.by_agent:
            return None
        
        agent_usage = self.by_agent[agent_name]
        display_name = self.AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
        
        return {
            "display_name": display_name,
            "calls": agent_usage.calls,
            "tokens": agent_usage.total_tokens,
            "prompt_tokens": agent_usage.prompt_tokens,
            "completion_tokens": agent_usage.completion_tokens,
            "cost": round(agent_usage.cost, 4),
            "average_tokens_per_call": round(agent_usage.total_tokens / max(agent_usage.calls, 1), 2)
        }

    def get_timeline(self) -> List[Dict]:
        """Get usage timeline for visualization"""
        timeline = []
        for i, usage in enumerate(self.usage_history):
            timeline.append({
                "index": i + 1,
                "model": usage.model,
                "tokens": usage.total_tokens,
                "cost": usage.cost
            })
        return timeline

    def reset(self):
        """Reset all tracking data"""
        self.usage_history.clear()
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.by_agent.clear()
        self.session_start = datetime.utcnow()
        logger.info("llm_tracker_reset")


tracker = LLMTracker()
