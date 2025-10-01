CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

--LEADS
CREATE TABLE leads (
    lead_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20) NOT NULL,
    nationality VARCHAR(100),
    language_preference VARCHAR(20) CHECK (language_preference IN ('arabic','english')),
    budget_min INT,
    budget_max INT,
    property_type VARCHAR(50) CHECK (property_type IN ('apartment','villa','townhouse','commercial')),
    preferred_areas TEXT[],
    status VARCHAR(30) DEFAULT 'new' CHECK (status IN ('new','contacted','qualified','viewing_scheduled','negotiation','converted','lost')),
    lead_score INT DEFAULT 0 CHECK (lead_score BETWEEN 0 AND 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deal_value NUMERIC(15,2)
);

ALTER TABLE leads ADD CONSTRAINT unique_phone_per_source UNIQUE (phone, source_type);

CREATE INDEX idx_leads_status ON leads (status);
CREATE INDEX idx_leads_property_type ON leads (property_type);
CREATE INDEX idx_leads_score ON leads (lead_score);

UPDATE leads
SET deal_value = 800000 + (random() * 3000000)
WHERE status = 'converted';
---------------------------------------------------------------------------------------------------------------------


--AGENTS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    specialization VARCHAR(100),
    preferred_areas TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    language VARCHAR(50) DEFAULT 'english',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookup
CREATE INDEX idx_agents_specialization ON agents (specialization);
CREATE INDEX idx_agents_active ON agents (is_active);

UPDATE agents
SET language = CASE
    WHEN random() < 0.5 THEN 'arabic'
    ELSE 'english'
END;
------------------------------------------------------------------------------------------------


--LEAD_ASSIGNMENT
CREATE TABLE lead_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reassigned BOOLEAN DEFAULT FALSE,
    reason VARCHAR(255), -- e.g. workload balancing, no response, manual reassignment
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE,
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT unique_lead_assignment UNIQUE (lead_id, agent_id, assigned_at)
);

CREATE INDEX idx_assignment_agent ON lead_assignments (agent_id);
CREATE INDEX idx_assignment_lead ON lead_assignments (lead_id);
CREATE INDEX idx_assignment_time ON lead_assignments (assigned_at DESC);
------------------------------------------------------------------------------------------------------


--LEAD_ACTIVITIES
CREATE TABLE lead_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    activity_type VARCHAR(30) NOT NULL CHECK (activity_type IN 
        ('call','email','whatsapp','viewing','meeting','offer_made')),
    notes TEXT,
    outcome VARCHAR(20) CHECK (outcome IN ('positive','negative','neutral')),
    next_follow_up TIMESTAMP ,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE,
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents (agent_id) ON DELETE CASCADE
);

CREATE INDEX idx_activity_lead ON lead_activities (lead_id);
CREATE INDEX idx_activity_agent ON lead_activities (agent_id);
CREATE INDEX idx_activity_type ON lead_activities (activity_type);
CREATE INDEX idx_activity_time ON lead_activities (created_at DESC);
-----------------------------------------------------------------------------------------------------


--LEAD_SCORING_RULES
CREATE TABLE lead_scoring_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(100) NOT NULL, 
    criteria JSONB NOT NULL,                 -- flexible rule definition
    score_delta INT NOT NULL,                -- + or - points
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scoring_rules_active ON lead_scoring_rules (is_active);
CREATE INDEX idx_scoring_rules_criteria ON lead_scoring_rules USING gin (criteria);
----------------------------------------------------------------------------------------------------------


--FOLLOW_UP_TASKS
CREATE TABLE follow_up_tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    task_type VARCHAR(30) NOT NULL CHECK (task_type IN ('call','email','whatsapp','viewing','meeting')),
    due_date TIMESTAMP NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE,
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents (agent_id) ON DELETE CASCADE
);

CREATE INDEX idx_tasks_agent ON follow_up_tasks (agent_id);
CREATE INDEX idx_tasks_lead ON follow_up_tasks (lead_id);
CREATE INDEX idx_tasks_due_date ON follow_up_tasks (due_date);


ALTER TABLE follow_up_tasks
ADD COLUMN completed_at TIMESTAMP;

UPDATE follow_up_tasks
SET completed = TRUE,
    completed_at = NOW()
WHERE task_id IN (
    SELECT task_id
    FROM follow_up_tasks
    ORDER BY random()
    LIMIT 15
);

-------------------------------------------------------------------------------------------------------------


--LEAD_PROPERTY_INTERESTS
CREATE TABLE lead_property_interests (
    interest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    property_id UUID NOT NULL,   -- Assume properties exist in another table or external system
    interest_level VARCHAR(20) NOT NULL CHECK (interest_level IN ('high','medium','low')),
    noted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    
    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE,
    CONSTRAINT unique_lead_property UNIQUE (lead_id, property_id)
);

CREATE INDEX idx_interest_lead ON lead_property_interests (lead_id);
CREATE INDEX idx_interest_property ON lead_property_interests (property_id);
CREATE INDEX idx_interest_level ON lead_property_interests (interest_level);
-----------------------------------------------------------------------------------------------------


--LEAD_SOURCES
CREATE TABLE lead_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('bayut','propertyFinder','dubizzle','website','walk_in','referral')),
    campaign_id VARCHAR(100),           -- e.g. spring_campaign_2024
    referrer_agent_id UUID,             -- if referral, links to another agent
    property_id UUID,                   -- if lead came from property inquiry
    utm_source VARCHAR(100),            -- e.g. google_ads, facebook, linkedin
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE,
    CONSTRAINT fk_referrer_agent FOREIGN KEY (referrer_agent_id) REFERENCES agents (agent_id) ON DELETE SET NULL
);

CREATE INDEX idx_sources_type ON lead_sources (source_type);
CREATE INDEX idx_sources_campaign ON lead_sources (campaign_id);
CREATE INDEX idx_sources_utm ON lead_sources (utm_source, utm_medium, utm_campaign);
-------------------------------------------------------------------------------------------------------------------


--AGENT_PERFORMANCE_METRICS
CREATE TABLE agent_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    date DATE NOT NULL,   -- daily or monthly aggregation date
    total_active_leads INT DEFAULT 0,
    overdue_follow_ups INT DEFAULT 0,
    conversions INT DEFAULT 0,
    average_response_time INTERVAL,   -- e.g. '4 hours'
    lead_score_average INT,
    conversion_rate NUMERIC(5,2),     -- percentage (0–100)
    average_deal_size NUMERIC(15,2),  -- AED
    response_time_rank INT,           -- relative rank among agents

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT unique_agent_date UNIQUE (agent_id, date) -- prevent duplicates per period
);

CREATE INDEX idx_metrics_agent ON agent_performance_metrics (agent_id);
CREATE INDEX idx_metrics_date ON agent_performance_metrics (date);
CREATE INDEX idx_metrics_conversion_rate ON agent_performance_metrics (conversion_rate DESC);
-------------------------------------------------------------------------------------------------------------


--LEAD_CONVERSION_HISTORY
CREATE TABLE lead_conversion_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL,
    previous_status VARCHAR(30) CHECK (previous_status IN ('new','contacted','qualified','viewing_scheduled','negotiation','converted','lost')),
    new_status VARCHAR(30) NOT NULL CHECK (new_status IN ('new','contacted','qualified','viewing_scheduled','negotiation','converted','lost')),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by UUID, -- optional: could be agent_id or supervisor id
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE
);

CREATE INDEX idx_history_lead ON lead_conversion_history (lead_id);
CREATE INDEX idx_history_new_status ON lead_conversion_history (new_status);
CREATE INDEX idx_history_time ON lead_conversion_history (changed_at DESC);
