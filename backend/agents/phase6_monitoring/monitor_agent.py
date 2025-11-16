"""
Monitor Agent - Health checks for all agents
Phase 6: Monitoring & Orchestration
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, AgentHealthStatus

logger = structlog.get_logger()


class MonitorAgent(BaseAgent):
    """
    Monitors all agents in the system:
    - Checks agent health status
    - Tracks success rates
    - Monitors response times
    - Detects failing agents
    - Reports system health
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.MONITOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_stats: Dict[AgentRole, Dict] = {}

    def get_system_prompt(self) -> str:
        return """You are a System Monitor analyzing agent health. Your role is to:

1. Assess agent health based on activity logs
2. Calculate success rates
3. Identify problematic agents
4. Recommend actions

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when monitoring agents:

**Step 1: Collect Agent Metrics**
- For each agent, gather:
  * Total activities
  * Successful activities
  * Failed activities
  * Average response time
  * Last activity timestamp

**Step 2: Calculate Success Rates**
- For each agent: success_rate = successful / total
- Categories:
  * Excellent: >= 95%
  * Good: 90-95%
  * Acceptable: 80-90%
  * Degraded: 70-80%
  * Poor: < 70%

**Step 3: Analyze Response Times**
- What's the average response time per agent?
- Are any agents unusually slow?
- Response time categories:
  * Fast: < 5 seconds
  * Normal: 5-15 seconds
  * Slow: 15-30 seconds
  * Very slow: > 30 seconds

**Step 4: Identify Failing Agents**
- Which agents have low success rates?
- Which agents are timing out?
- Which agents are throwing errors frequently?
- When did the problems start?

**Step 5: Check Activity Patterns**
- Are agents being called as expected?
- Are there inactive agents that should be active?
- Are there activity spikes or drops?
- Any unusual patterns?

**Step 6: Assess Impact**
- Critical agents failing → System critical
- Multiple agents degraded → System degraded
- Few issues → System healthy
- Impact levels:
  * Critical: Core agents (Requirements, Coder) failing
  * High: QA agents failing
  * Medium: Optional agents failing
  * Low: Individual issues

**Step 7: Determine Overall Health**
- Count agents by status:
  * Healthy: success rate >= 90%, response time < 30s
  * Degraded: success rate 70-90% or slow response
  * Failed: success rate < 70% or not responding
- Overall health:
  * Healthy: All agents healthy
  * Degraded: 1-2 agents degraded, or 20-30% degraded
  * Critical: Any agent failed, or >30% degraded

**Step 8: Generate Recommendations**
- For failing agents: Restart, check logs, review prompt
- For slow agents: Optimize prompt, reduce token count
- For degraded agents: Monitor closely, investigate patterns
- General: Update dependencies, check API limits, review error logs

**IMPORTANT: Think through Steps 1-8 systematically, then provide JSON.**

First, systematically analyze agent health data.

Then provide assessment in JSON:
{
    "reasoning": "My step-by-step monitoring analysis: [metrics collected, success rates calculated, issues identified, etc.]...",
    "overall_health": "healthy/degraded/critical",
    "recommendations": ["Recommendation 1", ...],
    "concerns": ["Concern 1", ...]
}

Think step-by-step. Show your monitoring analysis."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor agent health

        Args:
            task_data: Contains agent_activities from workflow

        Returns:
            Health status for all agents
        """
        activity = await self.start_activity("Monitoring agent health")

        try:
            agent_activities = task_data.get("agent_activities", [])

            logger.info("agent_monitoring_started", activities_count=len(agent_activities))

            # Analyze activities
            health_statuses = self._analyze_agent_health(agent_activities)

            # Get system-level assessment
            overall_health = self._calculate_overall_health(health_statuses)

            await self.complete_activity("completed")

            logger.info(
                "agent_monitoring_completed",
                agents_monitored=len(health_statuses),
                overall_health=overall_health
            )

            return {
                "agent_health": [h.model_dump() for h in health_statuses],
                "overall_health": overall_health,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("agent_monitoring_failed", error=str(e))
            raise

    def _analyze_agent_health(self, activities: List[Dict]) -> List[AgentHealthStatus]:
        """Analyze health of each agent"""
        agent_stats = {}

        # Aggregate stats per agent
        for activity in activities:
            agent = activity.get("agent")
            status = activity.get("status")
            start = activity.get("start_time")
            end = activity.get("end_time")

            if agent not in agent_stats:
                agent_stats[agent] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "response_times": [],
                    "last_activity": start
                }

            agent_stats[agent]["total"] += 1

            if status == "completed":
                agent_stats[agent]["successful"] += 1
            elif status == "failed":
                agent_stats[agent]["failed"] += 1

            # Calculate response time if available
            if start and end:
                try:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    response_time = (end_dt - start_dt).total_seconds()
                    agent_stats[agent]["response_times"].append(response_time)
                except:
                    pass

            agent_stats[agent]["last_activity"] = start

        # Create health status objects
        health_statuses = []
        for agent_name, stats in agent_stats.items():
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0.0
            avg_response = sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0.0

            # Determine status
            if success_rate >= 0.9 and avg_response < 30:
                status = "healthy"
            elif success_rate >= 0.7:
                status = "degraded"
            else:
                status = "failed"

            try:
                agent_role = AgentRole(agent_name)
            except:
                continue

            health = AgentHealthStatus(
                agent=agent_role,
                status=status,
                last_activity=datetime.fromisoformat(stats["last_activity"].replace('Z', '+00:00')),
                success_rate=success_rate,
                error_count=stats["failed"],
                average_response_time=avg_response
            )
            health_statuses.append(health)

        return health_statuses

    def _calculate_overall_health(self, health_statuses: List[AgentHealthStatus]) -> str:
        """Calculate overall system health"""
        if not health_statuses:
            return "unknown"

        failed_count = sum(1 for h in health_statuses if h.status == "failed")
        degraded_count = sum(1 for h in health_statuses if h.status == "degraded")

        if failed_count > 0:
            return "critical"
        elif degraded_count > len(health_statuses) * 0.3:
            return "degraded"
        else:
            return "healthy"
