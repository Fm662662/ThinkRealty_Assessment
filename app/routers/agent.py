from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
import json 

from app.db.redis_client import get_redis
from redis.asyncio import Redis

from app.schemas.agent import (
    AgentDashboardParams,
    AgentDashboardResponse,
    AgentSummary,
    RecentLeadItem,
    PendingTaskItem,
    PerformanceMetrics,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@router.get("/{agent_id}/dashboard", response_model=AgentDashboardResponse)
async def get_agent_dashboard(
    agent_id: UUID, params: AgentDashboardParams = Depends(), db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):

    cache_key = f"agent_dashboard:{agent_id}"
    
    cached = await redis.get(cache_key)
    if cached:
        return AgentDashboardResponse(**json.loads(cached))



    # --- 1. Agent summary ---
    summary_query = text("""
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
        LEFT JOIN follow_up_tasks f ON l.lead_id = f.lead_id
        LEFT JOIN lead_activities a ON l.lead_id = a.lead_id
        WHERE la.agent_id = :agent_id
    """)
    summary_res = await db.execute(summary_query, {"agent_id": str(agent_id)})
    summary_row = summary_res.mappings().first()

    agent_summary = AgentSummary(**summary_row)

    # --- 2. Recent leads (last 5) ---
    recent_query = text("""
        SELECT l.lead_id, l.first_name || ' ' || l.last_name AS name,
               l.phone, ls.source_type AS source, l.status, l.lead_score AS score,
               MAX(a.created_at) AS last_activity,
               MIN(f.due_date) FILTER (WHERE f.completed = FALSE) AS next_follow_up
        FROM leads l
        JOIN lead_assignments la ON l.lead_id = la.lead_id
        JOIN lead_sources ls ON l.lead_id = ls.lead_id
        LEFT JOIN lead_activities a ON l.lead_id = a.lead_id
        LEFT JOIN follow_up_tasks f ON l.lead_id = f.lead_id
        WHERE la.agent_id = :agent_id
        GROUP BY l.lead_id, l.first_name, l.last_name, l.phone, ls.source_type, l.status, l.lead_score
        ORDER BY MAX(a.created_at) DESC NULLS LAST
        LIMIT 5
    """)
    recent_res = await db.execute(recent_query, {"agent_id": str(agent_id)})
    recent_leads = [RecentLeadItem(**row) for row in recent_res.mappings().all()]

    # --- 3. Pending tasks (next 5) ---
    tasks_query = text("""
        SELECT f.task_id, l.first_name || ' ' || l.last_name AS lead_name,
               f.task_type, f.due_date, f.priority
        FROM follow_up_tasks f
        JOIN leads l ON f.lead_id = l.lead_id
        WHERE f.agent_id = :agent_id AND f.completed = FALSE
        ORDER BY f.due_date ASC
        LIMIT 5
    """)
    tasks_res = await db.execute(tasks_query, {"agent_id": str(agent_id)})
    pending_tasks = [PendingTaskItem(**row) for row in tasks_res.mappings().all()]

    # --- 4. Performance metrics ---
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
        raise HTTPException(status_code=404, detail="No metrics found for this agent")

    performance_metrics = PerformanceMetrics(**metrics_row)

    # --- Building full response ---
    response_Obj =  AgentDashboardResponse(
        agent_summary=agent_summary,
        recent_leads=recent_leads,
        pending_tasks=pending_tasks,
        performance_metrics=performance_metrics,
    )

    await redis.set(cache_key, json.dumps(response_Obj.dict()), ex=300)

    return response_Obj
