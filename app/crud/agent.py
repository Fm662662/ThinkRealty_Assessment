# app/crud/agent.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, desc, cast, String 
from uuid import UUID

from app.models import Lead, LeadAssignment, LeadSource, FollowUpTask, LeadActivity
from app.models import AgentPerformanceMetric


async def get_agent_summary(db: AsyncSession, agent_id: UUID, filters: list):
    """ Getting the agent summary based on agent_id """
    query = (
        select(
            func.count().filter(Lead.status.notin_(["converted", "lost"])).label("total_active_leads"),
            func.count(FollowUpTask.task_id).filter(
                and_(FollowUpTask.completed == False, FollowUpTask.due_date < func.now())
            ).label("overdue_follow_ups"),
            func.count().filter(
                and_(
                    Lead.status == "converted",
                    func.date_trunc("month", Lead.updated_at) == func.date_trunc("month", func.now())
                )
            ).label("this_month_conversions"),
            func.coalesce(
                func.concat(
                    cast(func.round(
                        func.avg(func.extract("epoch", (LeadActivity.created_at - Lead.created_at)) / 3600), 1), String), " hours"
                ),
                "N/A"
            ).label("average_response_time"),
            func.coalesce(func.round(func.avg(Lead.lead_score), 1), 0).label("lead_score_average"),
        )
        .join(LeadAssignment, Lead.lead_id == LeadAssignment.lead_id)
        .join(LeadSource, Lead.lead_id == LeadSource.lead_id)
        .outerjoin(FollowUpTask, Lead.lead_id == FollowUpTask.lead_id)
        .outerjoin(LeadActivity, Lead.lead_id == LeadActivity.lead_id)
        .where(*filters, LeadAssignment.agent_id == str(agent_id))
    )

    result = await db.execute(query)
    return result.mappings().first()


async def get_recent_leads(db: AsyncSession, agent_id: UUID, filters: list, limit: int = 5):
    """ Getting the last 5 leads """
    query = (
        select(
            Lead.lead_id,
            (Lead.first_name + " " + Lead.last_name).label("name"),
            Lead.phone,
            LeadSource.source_type.label("source"),
            Lead.status,
            Lead.lead_score.label("score"),
            func.max(LeadActivity.created_at).label("last_activity"),
            func.min(FollowUpTask.due_date).filter(FollowUpTask.completed == False).label("next_follow_up"),
        )
        .join(LeadAssignment, Lead.lead_id == LeadAssignment.lead_id)
        .join(LeadSource, Lead.lead_id == LeadSource.lead_id)
        .outerjoin(LeadActivity, Lead.lead_id == LeadActivity.lead_id)
        .outerjoin(FollowUpTask, Lead.lead_id == FollowUpTask.lead_id)
        .where(*filters, LeadAssignment.agent_id == str(agent_id))
        .group_by(
            Lead.lead_id,
            Lead.first_name,
            Lead.last_name,
            Lead.phone,
            LeadSource.source_type,
            Lead.status,
            Lead.lead_score,
        )
        .order_by(func.max(LeadActivity.created_at).desc().nullslast())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.mappings().all()


async def get_pending_tasks(db: AsyncSession, agent_id: UUID, filters: list, limit: int = 5):
    """ Getting the pending tasks (last 5) of that particular agent """
    query = (
        select(
            FollowUpTask.task_id,
            (Lead.first_name + " " + Lead.last_name).label("lead_name"),
            FollowUpTask.task_type,
            FollowUpTask.due_date,
            FollowUpTask.priority,
        )
        .join(Lead, Lead.lead_id == FollowUpTask.lead_id)
        .join(LeadAssignment, Lead.lead_id == LeadAssignment.lead_id)
        .join(LeadSource, Lead.lead_id == LeadSource.lead_id)
        .where(
            FollowUpTask.agent_id == str(agent_id),
            FollowUpTask.completed == False,
            *filters,
        )
        .order_by(FollowUpTask.due_date.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.mappings().all()


async def get_latest_performance_metrics(db: AsyncSession, agent_id: UUID) -> AgentPerformanceMetric | None:
    """
    Fetching the latest performance metrics for a given agent.
    Ordered by `date` descending, limit 1.
    """
    result = await db.execute(
        select(AgentPerformanceMetric)
        .where(AgentPerformanceMetric.agent_id == agent_id)
        .order_by(desc(AgentPerformanceMetric.date))
        .limit(1)
    )
    return result.scalars().first()
