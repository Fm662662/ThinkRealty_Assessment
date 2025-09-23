--FOR_RULE_2
CREATE OR REPLACE FUNCTION enforce_single_active_assignment()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM lead_assignments WHERE lead_id = NEW.lead_id AND reassigned = FALSE) > 0 THEN
        RAISE EXCEPTION 'Lead % already has an active assignment', NEW.lead_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_single_assignment
BEFORE INSERT ON lead_assignments
FOR EACH ROW EXECUTE FUNCTION enforce_single_active_assignment();

--FOR RULE 3
CREATE OR REPLACE FUNCTION enforce_lead_score()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure score is not below 0
    IF NEW.lead_score < 0 THEN
        NEW.lead_score := 0;
    END IF;

    -- Ensure score is not above 100
    IF NEW.lead_score > 100 THEN
        NEW.lead_score := 100;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: before inserting or updating leads
CREATE TRIGGER trg_enforce_lead_score
BEFORE INSERT OR UPDATE ON leads
FOR EACH ROW
EXECUTE FUNCTION enforce_lead_score();


--FOR_RULE_4
CREATE OR REPLACE FUNCTION check_followup_overdue()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.completed = FALSE AND NEW.due_date < NOW() - INTERVAL '30 days') THEN
        RAISE EXCEPTION 'Follow-up task overdue by more than 30 days for lead %', NEW.lead_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_followup_overdue
BEFORE INSERT OR UPDATE ON follow_up_tasks
FOR EACH ROW EXECUTE FUNCTION check_followup_overdue();


--FOR_RULE_5
CREATE OR REPLACE FUNCTION check_agent_workload()
RETURNS TRIGGER AS $$
DECLARE
    active_count INT;
BEGIN
    SELECT COUNT(*) INTO active_count
    FROM lead_assignments la
    JOIN leads l ON la.lead_id = l.lead_id
    WHERE la.agent_id = NEW.agent_id AND l.status NOT IN ('converted','lost');

    IF active_count >= 50 THEN
        RAISE EXCEPTION 'Agent % already has maximum workload of 50 active leads', NEW.agent_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_agent_workload
BEFORE INSERT ON lead_assignments
FOR EACH ROW EXECUTE FUNCTION check_agent_workload();


--FOR_RULE_6
CREATE OR REPLACE FUNCTION enforce_status_progression()
RETURNS TRIGGER AS $$
DECLARE
    valid BOOLEAN;
BEGIN
    valid := (
        (NEW.previous_status = 'new' AND NEW.new_status IN ('contacted')) OR
        (NEW.previous_status = 'contacted' AND NEW.new_status IN ('qualified')) OR
        (NEW.previous_status = 'qualified' AND NEW.new_status IN ('viewing_scheduled')) OR
        (NEW.previous_status = 'viewing_scheduled' AND NEW.new_status IN ('negotiation')) OR
        (NEW.previous_status = 'negotiation' AND NEW.new_status IN ('converted','lost'))
    );

    IF NOT valid THEN
        RAISE EXCEPTION 'Invalid status transition from % to % for lead %',
            NEW.previous_status, NEW.new_status, NEW.lead_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_status_progression
BEFORE INSERT ON lead_conversion_history
FOR EACH ROW EXECUTE FUNCTION enforce_status_progression();
---------------------------------------------------------------------------------------



-- Trigger function to auto-update `updated_at`
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update `updated_at` on row modification
CREATE TRIGGER trg_update_lead_sources
BEFORE UPDATE ON lead_sources
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
