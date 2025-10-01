from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

import itertools
from datetime import datetime

from app.models.agent import Agent
from app.models.lead import Lead
from app.models.agent_performance_metrics import AgentPerformanceMetric
from app.models.lead_assignment import LeadAssignment



class LeadAssignmentManager:
    """
        Service class responsible for assigning and reassigning leads to agents
        based on workload, specialization, language preference, and performance metrics.

        Responsibilities:
        1. Lead Assignment (`assign_lead`):
        - Ensures agents do not exceed 50 active leads.
        - Prefers agents with matching property type and preferred areas.
        - Matches language preference if specified.
        - Uses round-robin with weighted distribution (weights derived from
            agent performance metrics, e.g., conversion rate).

        2. Lead Reassignment (`reassign_lead`):
        - Marks previous assignment as inactive.
        - Supports manual reassignment (to a specific agent).
        - Supports automatic reassignment (best available agent).
        - Records reassignment reason for auditing.

        3. Workload Tracking (`get_agent_workload`):
        - Counts active leads per agent (excluding converted/lost leads and
            reassigned entries).
        - Used to enforce workload limits.

        4. Best Agent Selection (`find_best_agent`):
        - Applies filtering (specialization, preferred areas, language).
        - Considers agent performance metrics for weighting.
        - Maintains an in-memory round-robin cycle for fair distribution.

        Usage:
        - Called during lead capture (initial assignment).
        - Invoked when reassigning leads due to inactivity, workload balancing,
        or supervisor intervention.
        - Ensures fair and performance-driven distribution of leads across agents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._rr_cycle = None  # in-memory round robin cycle


    async def assign_lead(
        self,
        lead_id: UUID,
        lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assign a new lead to the best available agent.
        Rules:
        - Match agent specialization (property type, preferred areas).
        - Respect workload limit (≤ 50 active leads).
        - Match language preference if possible.
        - Round-robin with weighted distribution.
        """

        # 1. Fetch all agents with workload < 50
        subq = (
            select(func.count(LeadAssignment.assignment_id))
            .join(Lead, Lead.lead_id == LeadAssignment.lead_id)
            .where(
                LeadAssignment.agent_id == Agent.agent_id,
                LeadAssignment.reassigned == False,
                Lead.status.notin_(["converted", "lost"])
            )
        ).scalar_subquery()

        stmt = (
            select(
                Agent.agent_id,
                Agent.full_name,
                Agent.phone,
                Agent.language,
                Agent.specialization
            )
            .where(subq < 50)
        )
        result = await self.db.execute(stmt)
        agents = [dict(row._mapping) for row in result]

        if not agents:
            return None

        # 2. Filter by specialization (property type & preferred areas)
        property_type = lead_data.get("property_type")
        preferred_areas = lead_data.get("preferred_areas", [])

        if property_type:
            agents = [
                a for a in agents
                if a.get("specialization") and property_type in a["specialization"]
            ]

        if preferred_areas:
            agents = [
                a for a in agents
                if a.get("specialization") and set(preferred_areas).intersection(set(a["specialization"]))
            ] or agents  # fallback to all agents if none matched

        # 3. Try to match language preference if provided
        preferred_lang = lead_data.get("language_preference")
        if preferred_lang:
            matching_agents = [a for a in agents if a.get("language") == preferred_lang]
            if matching_agents:
                agents = matching_agents

        # 4. Use round-robin + weighted assignment
        chosen = await self.find_best_agent(lead_data)
        if not chosen:
            return None

        return {
            "agent_id": chosen["agent_id"],
            "full_name": chosen["full_name"],
            "phone": chosen["phone"]
        }


    async def reassign_lead(
        self,
        lead_id: UUID,
        reason: str,
        target_agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Reassign lead:
        - Mark old assignment as inactive (reassigned = TRUE).
        - Assign to a new agent (manual if target_agent_id, else auto).
        - Insert new assignment record.
        """

        # --- Step 1: Mark old assignment as reassigned ---
        await self.db.execute(
            update(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id, LeadAssignment.reassigned == False)
            .values(reassigned=True)
        )


        # --- Step 2: Determine new agent ---
        if target_agent_id:
            stmt = (
                select(Agent.agent_id, Agent.full_name, Agent.phone)
                .where(Agent.agent_id == target_agent_id)
            )
            result = await self.db.execute(stmt)
            new_agent = result.mappings().first()
            if not new_agent:
                raise ValueError(f"Agent {target_agent_id} not found")
        else:
            new_agent = await self.assign_lead(lead_id, lead_data={})
            if not new_agent:
                raise ValueError("No eligible agent available for reassignment")

        # --- Step 3: Insert new assignment ---
        new_assignment = LeadAssignment(
            assignment_id=uuid4(),
            lead_id=lead_id,
            agent_id=new_agent["agent_id"],
            reason=reason,
            reassigned=False,
            created_at=datetime.utcnow()
        )
        self.db.add(new_assignment)

        await self.db.commit()
        return new_agent

    async def get_assigned_agent(db, lead_id: str):
        # fetch the agent currently assigned to this lead
        stmt = select(LeadAssignment.agent_id).where(
            LeadAssignment.lead_id == lead_id
        ).order_by(LeadAssignment.created_at.desc())
        
        result = await db.execute(stmt)
        agent_id = result.scalar_one_or_none()  # latest assignment or None
        return agent_id


    async def get_agent_workload(self, agent_id: UUID) -> int:
        """
        Count active leads assigned to a given agent.
        Active = not converted/lost AND assignment not reassigned.
        """
        stmt = (
            select(func.count(LeadAssignment.assignment_id))
            .join(Lead, Lead.lead_id == LeadAssignment.lead_id)
            .where(
                LeadAssignment.agent_id == agent_id,
                LeadAssignment.reassigned == False,
                Lead.status.notin_(["converted", "lost"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def find_best_agent(self, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Core logic to find the most suitable agent:
        - Filters by workload (<50 active leads).
        - Prefers specialization (property type & preferred areas).
        - Prefers language match.
        - Uses round-robin with weighted distribution (based on conversion_rate).
        """

        # Subquery: workload check
        workload_subq = (
            select(func.count(LeadAssignment.assignment_id))
            .join(Lead, Lead.lead_id == LeadAssignment.lead_id)
            .where(
                LeadAssignment.agent_id == Agent.agent_id,
                LeadAssignment.reassigned == False,
                Lead.status.notin_(["converted", "lost"])
            )
        ).scalar_subquery()

        # Subquery: latest conversion rate
        latest_performance_subq = (
            select(AgentPerformanceMetric.conversion_rate)
            .where(AgentPerformanceMetric.agent_id == Agent.agent_id)
            .order_by(AgentPerformanceMetric.date.desc())
            .limit(1)
        ).scalar_subquery()

        stmt = (
            select(
                Agent.agent_id,
                Agent.full_name,
                Agent.phone,
                Agent.language,
                Agent.specialization,
                func.coalesce(latest_performance_subq, 1).label("weight")
            )
            .where(workload_subq < 50)
        )
        result = await self.db.execute(stmt)
        agents = [dict(row._mapping) for row in result]

        if not agents:
            return None

        # Specialization filtering
        property_type = lead_data.get("property_type")
        preferred_areas = lead_data.get("preferred_areas", [])

        if property_type:
            agents = [
                a for a in agents
                if a.get("specialization") and property_type in a["specialization"]
            ] or agents  # fallback if none matched

        if preferred_areas:
            agents = [
                a for a in agents
                if a.get("specialization") and set(preferred_areas).intersection(set(a["specialization"]))
            ] or agents

        # Language preference filter
        preferred_lang = lead_data.get("language_preference")
        if preferred_lang:
            matching_agents = [a for a in agents if a.get("language") == preferred_lang]
            if matching_agents:
                agents = matching_agents

        if not agents:
            return None

        # Build weighted pool (conversion_rate as weight) 
        weighted_pool = []
        for a in agents:
            weight = max(1, int(a["weight"]))  # at least 1
            weighted_pool.extend([a] * weight)

        # Initialize / reuse round robin cycle
        if not self._rr_cycle or not weighted_pool:
            self._rr_cycle = itertools.cycle(weighted_pool)

        chosen = next(self._rr_cycle)

        return {
            "agent_id": chosen["agent_id"],
            "full_name": chosen["full_name"],
            "phone": chosen["phone"]
        }

