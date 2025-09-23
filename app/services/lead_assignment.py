from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import random, itertools


class LeadAssignmentManager:
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
        result = await self.db.execute(
            text("""
                SELECT a.agent_id, a.full_name, a.phone, a.language, a.specialization
                FROM agents a
                WHERE (
                    SELECT COUNT(*)
                    FROM lead_assignments la
                    JOIN leads l ON la.lead_id = l.lead_id
                    WHERE la.agent_id = a.agent_id
                    AND l.status NOT IN ('converted','lost')
                    AND la.reassigned = FALSE
                ) < 50
            """)
        )
        agents = result.mappings().all()

        if not agents:
            return None  # no agent available

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

        # 1. Mark old assignment as reassigned
        await self.db.execute(
            text("""
                UPDATE lead_assignments
                SET reassigned = TRUE
                WHERE lead_id = :lead_id AND reassigned = FALSE
            """),
            {"lead_id": str(lead_id)},
        )

        # 2. Determine new agent
        if target_agent_id:
            # Manual reassignment
            result = await self.db.execute(
                text("SELECT agent_id, full_name, phone FROM agents WHERE agent_id = :aid"),
                {"aid": str(target_agent_id)},
            )
            new_agent = result.mappings().first()
            if not new_agent:
                raise ValueError(f"Agent {target_agent_id} not found")
        else:
            # Auto assignment using existing rules
            new_agent = await self.assign_lead(lead_id, lead_data={})
            if not new_agent:
                raise ValueError("No eligible agent available for reassignment")

        # 3. Insert new assignment
        await self.db.execute(
            text("""
                INSERT INTO lead_assignments (assignment_id, lead_id, agent_id, reason, reassigned)
                VALUES (:assignment_id, :lead_id, :agent_id, :reason, FALSE)
            """),
            {
                "assignment_id": str(uuid4()),
                "lead_id": str(lead_id),
                "agent_id": str(new_agent["agent_id"]),
                "reason": reason,
            },
        )

        return new_agent


    async def get_agent_workload(self, agent_id: UUID) -> int:
        """
        Count active leads assigned to a given agent.
        Active = not converted/lost AND assignment not reassigned.
        """

        result = await self.db.execute(
            text("""
                SELECT COUNT(*)
                FROM lead_assignments la
                JOIN leads l ON la.lead_id = l.lead_id
                WHERE la.agent_id = :agent_id
                AND la.reassigned = FALSE
                AND l.status NOT IN ('converted','lost')
            """),
            {"agent_id": str(agent_id)},
        )
        count = result.scalar() or 0
        return count


    async def find_best_agent(self, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Core logic to find the most suitable agent:
        - Filters by workload (<50 active leads).
        - Prefers specialization (property type & preferred areas).
        - Prefers language match.
        - Uses round-robin with weighted distribution (based on conversion_rate).
        """

        result = await self.db.execute(
            text("""
                SELECT a.agent_id, a.full_name, a.phone, a.language, a.specialization,
                       COALESCE(m.conversion_rate, 1) AS weight
                FROM agents a
                LEFT JOIN LATERAL (
                    SELECT conversion_rate
                    FROM agent_performance_metrics m
                    WHERE m.agent_id = a.agent_id
                    ORDER BY m.date DESC
                    LIMIT 1
                ) m ON TRUE
                WHERE (
                    SELECT COUNT(*)
                    FROM lead_assignments la
                    JOIN leads l ON la.lead_id = l.lead_id
                    WHERE la.agent_id = a.agent_id
                      AND l.status NOT IN ('converted','lost')
                      AND la.reassigned = FALSE
                ) < 50
            """)
        )
        agents = result.mappings().all()

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

