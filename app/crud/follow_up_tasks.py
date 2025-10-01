# crud/follow_up_tasks.py
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_

from app.models.follow_up_tasks import FollowUpTask


# Create a new follow-up task
async def create_task(
    db: AsyncSession,
    lead_id: UUID,
    agent_id: UUID,
    task_type: str,
    due_date: datetime,
    priority: str = "medium",
    notes: Optional[str] = None,
) -> FollowUpTask:
    task = FollowUpTask(
        task_id=uuid4(),
        lead_id=lead_id,
        agent_id=agent_id,
        task_type=task_type,
        due_date=due_date,
        priority=priority,
        notes=notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# Get task by ID
async def get_task(db: AsyncSession, task_id: UUID) -> Optional[FollowUpTask]:
    result = await db.execute(
        select(FollowUpTask).where(FollowUpTask.task_id == task_id)
    )
    return result.scalar_one_or_none()


# List all tasks for a lead
async def get_tasks_by_lead(db: AsyncSession, lead_id: UUID) -> List[FollowUpTask]:
    result = await db.execute(
        select(FollowUpTask).where(FollowUpTask.lead_id == lead_id)
    )
    return result.scalars().all()


# List all tasks for an agent
async def get_tasks_by_agent(db: AsyncSession, agent_id: UUID) -> List[FollowUpTask]:
    result = await db.execute(
        select(FollowUpTask).where(FollowUpTask.agent_id == agent_id)
    )
    return result.scalars().all()


# Get overdue tasks for an agent
async def get_overdue_tasks(db: AsyncSession, agent_id: UUID) -> List[FollowUpTask]:
    now = datetime.utcnow()
    result = await db.execute(
        select(FollowUpTask).where(
            and_(
                FollowUpTask.agent_id == agent_id,
                FollowUpTask.due_date < now,
                FollowUpTask.completed == False,
            )
        )
    )
    return result.scalars().all()


# Mark task as completed
async def mark_task_completed(db: AsyncSession, task_id: UUID) -> Optional[FollowUpTask]:
    stmt = (
        update(FollowUpTask)
        .where(FollowUpTask.task_id == task_id)
        .values(completed=True, completed_at=datetime.utcnow(), updated_at=datetime.utcnow())
        .returning(FollowUpTask)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


# Update task fields
async def update_task(
    db: AsyncSession,
    task_id: UUID,
    task_type: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None,
    completed: Optional[bool] = None,
) -> Optional[FollowUpTask]:
    values = {"updated_at": datetime.utcnow()}
    if task_type is not None:
        values["task_type"] = task_type
    if due_date is not None:
        values["due_date"] = due_date
    if priority is not None:
        values["priority"] = priority
    if notes is not None:
        values["notes"] = notes
    if completed is not None:
        values["completed"] = completed
        if completed:
            values["completed_at"] = datetime.utcnow()

    stmt = (
        update(FollowUpTask)
        .where(FollowUpTask.task_id == task_id)
        .values(**values)
        .returning(FollowUpTask)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


# Delete a task
async def delete_task(db: AsyncSession, task_id: UUID) -> bool:
    stmt = delete(FollowUpTask).where(FollowUpTask.task_id == task_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
