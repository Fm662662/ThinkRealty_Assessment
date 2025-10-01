# crud/lead_activities.py
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from datetime import datetime

from app.models.lead_activities import LeadActivity


# Create a new activity
async def create_activity(
    db: AsyncSession,
    lead_id: UUID,
    agent_id: UUID,
    activity_type: str,
    notes: Optional[str] = None,
    outcome: Optional[str] = None,
    next_follow_up: Optional[datetime] = None,
) -> LeadActivity:
    activity = LeadActivity(
        activity_id=uuid4(),
        lead_id=lead_id,
        agent_id=agent_id,
        activity_type=activity_type,
        notes=notes,
        outcome=outcome,
        next_follow_up=next_follow_up,
        created_at=datetime.utcnow(),
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


# Get a single activity by ID
async def get_activity(db: AsyncSession, activity_id: UUID) -> Optional[LeadActivity]:
    result = await db.execute(
        select(LeadActivity).where(LeadActivity.activity_id == activity_id)
    )
    return result.scalar_one_or_none()


# List all activities for a lead
async def get_activities_by_lead(db: AsyncSession, lead_id: UUID) -> List[LeadActivity]:
    result = await db.execute(
        select(LeadActivity).where(LeadActivity.lead_id == lead_id).order_by(LeadActivity.created_at.desc())
    )
    return result.scalars().all()


# List all activities for an agent
async def get_activities_by_agent(db: AsyncSession, agent_id: UUID) -> List[LeadActivity]:
    result = await db.execute(
        select(LeadActivity).where(LeadActivity.agent_id == agent_id).order_by(LeadActivity.created_at.desc())
    )
    return result.scalars().all()


# Update activity (notes, outcome, next_follow_up)
async def update_activity(
    db: AsyncSession,
    activity_id: UUID,
    notes: Optional[str] = None,
    outcome: Optional[str] = None,
    next_follow_up: Optional[datetime] = None,
) -> Optional[LeadActivity]:
    stmt = (
        update(LeadActivity)
        .where(LeadActivity.activity_id == activity_id)
        .values(
            notes=notes,
            outcome=outcome,
            next_follow_up=next_follow_up,
        )
        .returning(LeadActivity)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


# Delete activity
async def delete_activity(db: AsyncSession, activity_id: UUID) -> bool:
    stmt = delete(LeadActivity).where(LeadActivity.activity_id == activity_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
