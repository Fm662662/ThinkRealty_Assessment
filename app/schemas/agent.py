from typing import List, Optional, Literal
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

# --- Query params ---
class AgentDashboardParams(BaseModel):
    date_range: Literal["7d", "30d", "90d", "custom"] = "30d"
    status_filter: Literal["all", "active", "converted", "lost"] = "all"
    source_filter: Literal["all", "bayut", "propertyFinder", "dubizzle", "website", "walk_in", "referral"] = "all"
    # used only when date_range == "custom"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Response submodels ---
class AgentSummary(BaseModel):
    total_active_leads: int
    overdue_follow_ups: int
    this_month_conversions: int
    average_response_time: str
    lead_score_average: float

    model_config = {"from_attributes": True}


class RecentLeadItem(BaseModel):
    lead_id: UUID
    name: str
    phone: str
    source: str
    status: str
    score: int
    last_activity: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PendingTaskItem(BaseModel):
    task_id: UUID
    lead_name: str
    task_type: Literal["call", "email", "whatsapp", "viewing", "meeting"]
    due_date: datetime
    priority: Literal["high", "medium", "low"]

    model_config = {"from_attributes": True}


class PerformanceMetrics(BaseModel):
    conversion_rate: float
    average_deal_size: float
    response_time_rank: int

    model_config = {"from_attributes": True}


# --- Full response model ---
class AgentDashboardResponse(BaseModel):
    agent_summary: AgentSummary
    recent_leads: List[RecentLeadItem]
    pending_tasks: List[PendingTaskItem]
    performance_metrics: PerformanceMetrics

    model_config = {"from_attributes": True}
