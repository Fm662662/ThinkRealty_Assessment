from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
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


from datetime import datetime, timedelta

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

        # --- Build dynamic filters ---
        filters = ["la.agent_id = :agent_id"]
        query_params = {"agent_id": str(agent_id)}

        # Date range filter
        if params.date_range and params.date_range != "all":
            if params.date_range in ("7d", "30d", "90d"):
                days = int(params.date_range.replace("d", ""))
                filters.append("l.created_at >= NOW() - make_interval(days => :days)")
                query_params["days"] = days
            elif params.date_range == "custom" and params.start_date and params.end_date:
                filters.append("l.created_at BETWEEN :start_date AND :end_date")
                query_params["start_date"] = params.start_date
                query_params["end_date"] = params.end_date

        # Status filter
        if params.status_filter and params.status_filter != "all":
            if params.status_filter == "active":
                filters.append("l.status NOT IN ('converted','lost')")
            elif params.status_filter == "converted":
                filters.append("l.status = 'converted'")
            elif params.status_filter == "lost":
                filters.append("l.status = 'lost'")

        # Source filter
        if params.source_filter and params.source_filter != "all":
            filters.append("ls.source_type = :source_type")
            query_params["source_type"] = params.source_filter

        where_clause = " AND ".join(filters)

        # 2. --- Agent summary ---
        summary_query = text(f"""
            SELECT
                COUNT(*) FILTER (WHERE l.status NOT IN ('converted','lost')) AS total_active_leads,
                COUNT(f.*) FILTER (
                    WHERE f.completed = FALSE AND f.due_date < NOW()
                ) AS overdue_follow_ups,
                COUNT(*) FILTER (
                    WHERE l.status = 'converted'
                    AND DATE_TRUNC('month', l.updated_at) = DATE_TRUNC('month', NOW())
                ) AS this_month_conversions,
                COALESCE(ROUND(AVG(EXTRACT(EPOCH FROM (a.created_at - l.created_at))/3600),1) || ' hours', 'N/A') AS average_response_time,
                COALESCE(ROUND(AVG(l.lead_score),1),0) AS lead_score_average
            FROM leads l
            JOIN lead_assignments la ON l.lead_id = la.lead_id
            JOIN lead_sources ls ON l.lead_id = ls.lead_id
            LEFT JOIN follow_up_tasks f ON l.lead_id = f.lead_id
            LEFT JOIN lead_activities a ON l.lead_id = a.lead_id
            WHERE {where_clause}
        """)
        summary_res = await db.execute(summary_query, query_params)
        summary_row = summary_res.mappings().first()
        agent_summary = AgentSummary(**summary_row)

        # 3. --- Recent leads (last 5) ---
        recent_query = text(f"""
            SELECT l.lead_id, l.first_name || ' ' || l.last_name AS name,
                   l.phone, ls.source_type AS source, l.status, l.lead_score AS score,
                   MAX(a.created_at) AS last_activity,
                   MIN(f.due_date) FILTER (WHERE f.completed = FALSE) AS next_follow_up
            FROM leads l
            JOIN lead_assignments la ON l.lead_id = la.lead_id
            JOIN lead_sources ls ON l.lead_id = ls.lead_id
            LEFT JOIN lead_activities a ON l.lead_id = a.lead_id
            LEFT JOIN follow_up_tasks f ON l.lead_id = f.lead_id
            WHERE {where_clause}
            GROUP BY l.lead_id, l.first_name, l.last_name, l.phone, ls.source_type, l.status, l.lead_score
            ORDER BY MAX(a.created_at) DESC NULLS LAST
            LIMIT 5
        """)
        recent_res = await db.execute(recent_query, query_params)
        recent_leads = [RecentLeadItem(**row) for row in recent_res.mappings().all()]

        # 4. --- Pending tasks (limit 5) ---
        tasks_query = text(f"""
            SELECT f.task_id, l.first_name || ' ' || l.last_name AS lead_name,
                   f.task_type, f.due_date, f.priority
            FROM follow_up_tasks f
            JOIN leads l ON f.lead_id = l.lead_id
            JOIN lead_assignments la ON l.lead_id = la.lead_id
            JOIN lead_sources ls ON l.lead_id = ls.lead_id
            WHERE f.agent_id = :agent_id AND f.completed = FALSE
              AND {where_clause}
            ORDER BY f.due_date ASC
            LIMIT 5
        """)
        tasks_res = await db.execute(tasks_query, query_params)
        pending_tasks = [PendingTaskItem(**row) for row in tasks_res.mappings().all()]

        # 5. --- Performance metrics ---
        metrics_query = text("""
            SELECT conversion_rate, average_deal_size, response_time_rank
            FROM agent_performance_metrics
            WHERE agent_id = :agent_id
            ORDER BY date DESC
            LIMIT 1
        """)
        metrics_res = await db.execute(metrics_query, {"agent_id": str(agent_id)})
        metrics_row = metrics_res.mappings().first()

        if not metrics_row:
            raise Exception("No metrics found for this agent")

        performance_metrics = PerformanceMetrics(**metrics_row)

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
