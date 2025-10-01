# crud/lead_source.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
from uuid import UUID

from app.models.lead_sources import LeadSource


# ---------------- CREATE ----------------
async def create_source(
    db: AsyncSession,
    lead_id: UUID,
    source_type: str,
    campaign_id: Optional[str] = None,
    referrer_agent_id: Optional[UUID] = None,
    property_id: Optional[UUID] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
) -> LeadSource:
    source = LeadSource(
        lead_id=lead_id,
        source_type=source_type,
        campaign_id=campaign_id,
        referrer_agent_id=referrer_agent_id,
        property_id=property_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


# ---------------- READ ----------------
async def get_source(db: AsyncSession, source_id: UUID) -> Optional[LeadSource]:
    result = await db.execute(
        select(LeadSource).where(LeadSource.source_id == source_id)
    )
    return result.scalar_one_or_none()


async def get_sources_by_lead(db: AsyncSession, lead_id: UUID) -> List[LeadSource]:
    result = await db.execute(
        select(LeadSource).where(LeadSource.lead_id == lead_id)
    )
    return result.scalars().all()


# ---------------- UPDATE ----------------
async def update_source(
    db: AsyncSession,
    source_id: UUID,
    **kwargs
) -> Optional[LeadSource]:
    """
    kwargs can include: source_type, campaign_id, referrer_agent_id,
    property_id, utm_source, utm_medium, utm_campaign
    """
    result = await db.execute(
        update(LeadSource)
        .where(LeadSource.source_id == source_id)
        .values(**kwargs)
        .returning(LeadSource)
    )
    await db.commit()
    return result.scalar_one_or_none()


# ---------------- DELETE ----------------
async def delete_source(db: AsyncSession, source_id: UUID) -> bool:
    result = await db.execute(
        delete(LeadSource).where(LeadSource.source_id == source_id)
    )
    await db.commit()
    return result.rowcount > 0
