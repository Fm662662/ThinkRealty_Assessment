# crud/lead_scoring_rule.py
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from datetime import datetime

from app.models.lead_scoring_rules import LeadScoringRule


# Create a new scoring rule
async def create_rule(
    db: AsyncSession,
    rule_name: str,
    criteria: dict,
    score_delta: int,
    is_active: bool = True,
) -> LeadScoringRule:
    rule = LeadScoringRule(
        rule_id=uuid4(),
        rule_name=rule_name,
        criteria=criteria,
        score_delta=score_delta,
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


# Get a rule by ID
async def get_rule(db: AsyncSession, rule_id: UUID) -> Optional[LeadScoringRule]:
    result = await db.execute(
        select(LeadScoringRule).where(LeadScoringRule.rule_id == rule_id)
    )
    return result.scalar_one_or_none()


# List all active rules
async def get_active_rules(db: AsyncSession) -> List[LeadScoringRule]:
    result = await db.execute(
        select(LeadScoringRule).where(LeadScoringRule.is_active == True)
    )
    return result.scalars().all()


# List all rules (active + inactive)
async def get_all_rules(db: AsyncSession) -> List[LeadScoringRule]:
    result = await db.execute(select(LeadScoringRule))
    return result.scalars().all()


# Update a rule
async def update_rule(
    db: AsyncSession,
    rule_id: UUID,
    rule_name: Optional[str] = None,
    criteria: Optional[dict] = None,
    score_delta: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> Optional[LeadScoringRule]:
    stmt = (
        update(LeadScoringRule)
        .where(LeadScoringRule.rule_id == rule_id)
        .values(
            rule_name=rule_name,
            criteria=criteria,
            score_delta=score_delta,
            is_active=is_active,
        )
        .returning(LeadScoringRule)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()


# Delete a rule
async def delete_rule(db: AsyncSession, rule_id: UUID) -> bool:
    stmt = delete(LeadScoringRule).where(LeadScoringRule.rule_id == rule_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
