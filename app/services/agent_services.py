from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Interval
from sqlalchemy import func, text
from uuid import UUID
from redis.asyncio import Redis
import json

from app.schemas.agent import (
    AgentDashboardParams,
    AgentDashboardResponse,
    AgentSummary,
    RecentLeadItem,
    PendingTaskItem,
    PerformanceMetrics,
)

from app.models import Lead, LeadSource
from app.crud import agent as crud_agent

class AgentServices:
    """
        Service class for managing agent dashboard operations.

        This class provides methods to assemble and return a real estate agent's 
        dashboard data by combining information from leads, assignments, tasks, 
        and performance metrics. It supports caching, filtering, and query customization.

        Features:
            - Retrieves agent summary (active leads, overdue follow-ups, monthly conversions,
            average response time, average lead score).
            - Retrieves the 5 most recent leads handled by the agent.
            - Retrieves the 5 most urgent pending follow-up tasks.
            - Retrieves the latest performance metrics (conversion rate, average deal size, response time rank).
            - Supports filters for date range, lead status, and source.
            - Uses Redis for caching the assembled dashboard response (default 5 minutes).

        Methods:
            get_agent_dashboard(agent_id, params, db, redis):
                Build and return the agent dashboard response for the given agent, 
                applying optional filters and caching results in Redis.

        Args:
            agent_id (UUID): The unique identifier of the agent.
            params (AgentDashboardParams): Dashboard filters (date_range, status_filter, source_filter, start_date, end_date).
            db (AsyncSession): SQLAlchemy asynchronous database session.
            redis (Redis): Redis client instance for caching.

        Returns:
            AgentDashboardResponse: Aggregated dashboard data including:
                - agent_summary (AgentSummary)
                - recent_leads (list of RecentLeadItem)
                - pending_tasks (list of PendingTaskItem)
                - performance_metrics (PerformanceMetrics)

        Raises:
            Exception: If no performance metrics are found for the agent.
    """
    @staticmethod
    async def get_agent_dashboard(
        agent_id: UUID,
        params: AgentDashboardParams,
        db: AsyncSession,
        redis: Redis,
    ) -> AgentDashboardResponse:
        cache_key = f"agent_dashboard:{agent_id}:{params.json()}"  # cache per filter

        # 1. --- Checking Redis cache ---
        cached = await redis.get(cache_key)
        if cached:
            return AgentDashboardResponse(**json.loads(cached))

        # --- Build ORM filters ---
        filters = []

        # Date range filter
        if params.date_range and params.date_range != "all":
            if params.date_range in ("7d", "30d", "90d"):
                days = int(params.date_range.replace("d", ""))
                filters.append(
                    Lead.created_at >= text(f"NOW() - INTERVAL '{days} days'")
                )
            elif (
                params.date_range == "custom"
                and params.start_date
                and params.end_date
            ):
                filters.append(
                    Lead.created_at.between(params.start_date, params.end_date)
                )

        # Status filter
        if params.status_filter and params.status_filter != "all":
            if params.status_filter == "active":
                filters.append(Lead.status.notin_(["converted", "lost"]))
            elif params.status_filter == "converted":
                filters.append(Lead.status == "converted")
            elif params.status_filter == "lost":
                filters.append(Lead.status == "lost")

        # Source filter
        if params.source_filter and params.source_filter != "all":
            filters.append(LeadSource.source_type == params.source_filter)

        # 2. --- Agent summary ---
        summary_row = await crud_agent.get_agent_summary(db, agent_id, filters)
        agent_summary = AgentSummary(**summary_row)

        # 3. --- Recent leads (last 5) ---
        recent_rows = await crud_agent.get_recent_leads(db, agent_id, filters, limit=5)
        recent_leads = [RecentLeadItem(**row) for row in recent_rows]

        # 4. --- Pending tasks (limit 5) ---
        task_rows = await crud_agent.get_pending_tasks(db, agent_id, filters, limit=5)
        pending_tasks = [PendingTaskItem(**row) for row in task_rows]

        # 5. --- Performance metrics ---
        metrics_row = await crud_agent.get_latest_performance_metrics(db, agent_id)
        if not metrics_row:
            raise Exception("No metrics found for this agent")
        performance_metrics = PerformanceMetrics.from_orm(metrics_row)

        # --- Build final response ---
        response_obj = AgentDashboardResponse(
            agent_summary=agent_summary,
            recent_leads=recent_leads,
            pending_tasks=pending_tasks,
            performance_metrics=performance_metrics,
        )

        # Cache in Redis (5 min)
        await redis.set(cache_key, json.dumps(response_obj.dict(), default=str), ex=300)

        return response_obj
