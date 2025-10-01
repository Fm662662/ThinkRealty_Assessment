--Insertion_into_leads_table
INSERT INTO leads (source_type, first_name, last_name, email, phone, nationality, language_preference, budget_min, budget_max, property_type, preferred_areas, status, lead_score)
SELECT
  (ARRAY['bayut','dubizzle','propertyFinder','website','walk_in'])[floor(random()*5)+1],
  'LeadFirst' || i,
  'LeadLast' || i,
  'lead' || i || '@mail.com',
  '+97150' || lpad(i::text, 7, '0'),
  (ARRAY['UAE','India','UK','Egypt','China','Pakistan'])[floor(random()*6)+1],
  (ARRAY['arabic','english'])[floor(random()*2)+1],
  (500000 + (random()*2000000))::INT,
  (1500000 + (random()*3000000))::INT,
  (ARRAY['apartment','villa','townhouse','commercial'])[floor(random()*4)+1],
  ARRAY['Dubai Marina','Downtown Dubai','JBR','Palm Jumeirah','Business Bay'],
  (ARRAY['new','contacted','qualified','viewing_scheduled','negotiation','converted','lost'])[floor(random()*7)+1],
  (floor(random()*101))::INT
FROM generate_series(1, 105) s(i);
----------------------------------------------------------------------------------------------------------------------------------


--Insertion_into_agents_table
INSERT INTO agents (full_name, email, phone, specialization, preferred_areas)
VALUES
('Sarah Johnson', 'sarah.johnson@thinkrealty.ae', '+971501234561', 'apartment', '{"Downtown Dubai","Marina"}'),
('Ahmed Al Mansoori', 'ahmed.mansoori@thinkrealty.ae', '+971501234562', 'villa', '{"Palm Jumeirah","Jumeirah Village"}'),
('Fatima Hassan', 'fatima.hassan@thinkrealty.ae', '+971501234563', 'townhouse', '{"Arabian Ranches","DAMAC Hills"}'),
('David Chen', 'david.chen@thinkrealty.ae', '+971501234564', 'commercial', '{"Business Bay","DIFC"}'),
('Maria Gonzalez', 'maria.gonzalez@thinkrealty.ae', '+971501234565', 'apartment', '{"JBR","Dubai Hills"}'),
('Omar Khalid', 'omar.khalid@thinkrealty.ae', '+971501234572', 'villa', '{"Mirdif","Al Barsha"}'),
('Sophia Lee', 'sophia.lee@thinkrealty.ae', '+971501234573', 'apartment', '{"Dubai Hills","Silicon Oasis"}'),
('Mohammed Rashid', 'mohammed.rashid@thinkrealty.ae', '+971501234574', 'commercial', '{"Deira","Bur Dubai"}'),
('Emily Carter', 'emily.carter@thinkrealty.ae', '+971501234575', 'townhouse', '{"DAMAC Hills","Arabian Ranches"}'),
('Hassan Ali', 'hassan.ali@thinkrealty.ae', '+971501234576', 'apartment', '{"Sports City","Discovery Gardens"}');
----------------------------------------------------------------------------------------------------------------------------------

--Insertion_into_lead_activities_table
INSERT INTO lead_activities (lead_id, agent_id, activity_type, notes, outcome, next_follow_up)
SELECT sub.l,
       sub.a,
       (ARRAY['call','email','whatsapp','viewing','meeting','offer_made'])[floor(random()*6)+1],
       'Auto-generated activity ' || gs.i,
       (ARRAY['positive','neutral','negative'])[floor(random()*3)+1],
       NOW() + ((random()*10)::INT || ' days')::INTERVAL
FROM generate_series(1,55) gs(i)
CROSS JOIN LATERAL (
    SELECT l.lead_id AS l, a.agent_id AS a
    FROM leads l
    JOIN agents a ON random() < 0.1
    ORDER BY random()
    LIMIT 1
) AS sub;
-------------------------------------------------------------------------------------------------------------------------------

--Insertion_into_lead_assignments_table
-- -- Step 1: Get eligible leads (status not converted/lost) and number them
WITH eligible_leads AS (
    SELECT lead_id, ROW_NUMBER() OVER (ORDER BY lead_id) AS rn
    FROM leads
    WHERE status NOT IN ('converted','lost')
),

-- -- Step 2: Get agents with their current active lead count
eligible_agents AS (
    SELECT a.agent_id, 
           COUNT(la.lead_id) AS active_count,
           ROW_NUMBER() OVER (ORDER BY a.agent_id) AS agent_rn
    FROM agents a
    LEFT JOIN lead_assignments la 
           ON la.agent_id = a.agent_id 
           AND la.reassigned = FALSE
    LEFT JOIN leads l 
           ON l.lead_id = la.lead_id 
           AND l.status NOT IN ('converted','lost')
    GROUP BY a.agent_id
    HAVING COUNT(la.lead_id) < 50  -- only agents with <50 leads
),

-- -- Step 3: Assign each lead to an agent in a round-robin way
assignments AS (
    SELECT el.lead_id,
           a.agent_id,
           'initial assignment' AS reason
    FROM eligible_leads el
    JOIN eligible_agents a
      ON ((el.rn - 1) % (SELECT COUNT(*) FROM eligible_agents)) + 1 = a.agent_rn
)

-- -- Step 4: Insert assignments
INSERT INTO lead_assignments (lead_id, agent_id, reason)
SELECT lead_id, agent_id, reason
FROM assignments;
-----------------------------------------------------------------------------------------------------------------------------


--Insertion_into_lead_activites
INSERT INTO lead_activities (lead_id, agent_id, activity_type, notes, outcome, next_follow_up)
SELECT sub.lead_id,
       sub.agent_id,
       (ARRAY['call','email','whatsapp','viewing','meeting','offer_made'])[floor(random()*6)+1],
       'Auto-generated activity ' || gs.i,
       (ARRAY['positive','neutral','negative'])[floor(random()*3)+1],
       NOW() + ((random()*10)::INT || ' days')::INTERVAL
FROM generate_series(1,55) gs(i)
JOIN LATERAL (
    SELECT l.lead_id, a.agent_id
    FROM leads l
    JOIN agents a ON random() < 0.1
    ORDER BY random()
    LIMIT 1
) AS sub ON TRUE;
---------------------------------------------------------------------------------------------------------------------------------


--Insertion_into_lead_scoring_rules
INSERT INTO lead_scoring_rules (rule_name, criteria, score_delta)
VALUES
-- Budget rules
('High Budget Bonus', '{"field":"budget_max","operator":">","value":1500000}', 15),
('Mid Budget Bonus', '{"field":"budget_max","operator":">","value":1000000}', 8),
('Low Budget Penalty', '{"field":"budget_max","operator":"<","value":500000}', -5),

-- Source quality rules
('Source Quality - Bayut', '{"field":"source_type","operator":"=","value":"bayut"}', 10),
('Source Quality - PropertyFinder', '{"field":"source_type","operator":"=","value":"propertyFinder"}', 8),
('Source Quality - Website', '{"field":"source_type","operator":"=","value":"website"}', 5),
('Source Quality - Dubizzle', '{"field":"source_type","operator":"=","value":"dubizzle"}', 3),

-- Nationality bonus
('UAE Nationality Bonus', '{"field":"nationality","operator":"=","value":"UAE"}', 10),
('GCC Nationality Bonus', '{"field":"nationality","operator":"IN","value":["KSA","Kuwait","Oman","Bahrain","Qatar"]}', 5),

-- Activity-based rules
('Positive Call Outcome', '{"field":"activity_type","operator":"=","value":"call","outcome":"positive"}', 5),
('Viewing Scheduled', '{"field":"activity_type","operator":"=","value":"viewing"}', 10),
('Offer Made', '{"field":"activity_type","operator":"=","value":"offer_made"}', 20),
('No Response Penalty', '{"field":"days_inactive","operator":">","value":7}', -10),

-- Referral bonus
('Referral Bonus', '{"field":"referrer_agent_id","operator":"NOT_NULL"}', 5);
-----------------------------------------------------------------------------------------------------------------------------------

--Insert_into_follow_up_tasks
INSERT INTO follow_up_tasks (lead_id, agent_id, task_type, due_date, priority, notes)
SELECT sub.lead_id, sub.agent_id,
       (ARRAY['call','email','whatsapp','viewing','meeting'])[floor(random()*5)+1],
       NOW() + ((random()*15)::INT || ' days')::INTERVAL,
       (ARRAY['high','medium','low'])[floor(random()*3)+1],
       'Auto-generated follow-up ' || gs.i
FROM generate_series(1,50) gs(i)
CROSS JOIN LATERAL (
    SELECT l.lead_id, a.agent_id
    FROM leads l
    JOIN agents a ON random() < 0.1
    ORDER BY random()
    LIMIT 1
) AS sub
ON CONFLICT (lead_id, due_date) DO NOTHING;
-------------------------------------------------------------------------------------------------------------------------


--Insertion_into_lead_property_interests_table
INSERT INTO lead_property_interests (lead_id, property_id, interest_level)
SELECT
  (SELECT lead_id FROM leads ORDER BY random() LIMIT 1),
  gen_random_uuid(),
  (CASE (floor(random() * 3))
    WHEN 0 THEN 'high'
    WHEN 1 THEN 'medium'
    ELSE 'low'
  END)
FROM generate_series(1, 20);


--Insert_into_lead_sources_table
INSERT INTO lead_sources (lead_id, source_type, campaign_id, utm_source, utm_medium, utm_campaign)
SELECT l.lead_id,
       (ARRAY['bayut','dubizzle','propertyFinder','website','walk_in','referral'])[floor(random()*6)+1],
       'campaign_' || (floor(random()*5)+1),
       (ARRAY['google_ads','facebook_ads','linkedin','organic','direct'])[floor(random()*5)+1],
       (ARRAY['cpc','social','search','referral','form'])[floor(random()*5)+1],
       'utm_campaign_' || (floor(random()*10)+1)
FROM leads l
ON CONFLICT DO NOTHING;


--Insert_into_agent_performance_metrics_table
INSERT INTO agent_performance_metrics 
(agent_id, date, total_active_leads, overdue_follow_ups, conversions, average_response_time, lead_score_average, conversion_rate, average_deal_size, response_time_rank)
VALUES
((SELECT agent_id FROM agents WHERE full_name='Sarah Johnson'), CURRENT_DATE, 23, 5, 8, INTERVAL '4 hours 30 minutes', 67, 15.5, 1200000, 3),
((SELECT agent_id FROM agents WHERE full_name='Ahmed Al Mansoori'), CURRENT_DATE, 18, 2, 5, INTERVAL '3 hours', 72, 12.0, 2500000, 2),
((SELECT agent_id FROM agents WHERE full_name='Maria Gonzalez'), CURRENT_DATE, 12, 1, 4, INTERVAL '2 hours 15 minutes', 80, 18.5, 1800000, 1),
((SELECT agent_id FROM agents WHERE full_name='David Chen'), CURRENT_DATE, 20, 3, 6, INTERVAL '5 hours', 60, 14.2, 3500000, 4),
((SELECT agent_id FROM agents WHERE full_name='Fatima Hassan'), CURRENT_DATE, 15, 4, 3, INTERVAL '6 hours', 55, 9.5, 1100000, 5);

--IN REAL TIME THE INSERTION WOULD BE CARRIED OUT LIKE BELOW BUT FOR NOW I HAVE USED THE ABOVE METHOD TO FILL THE DUMMY DATA IN TABLE agent_performance_metrics
-- INSERT INTO agent_performance_metrics 
-- (agent_id, date, total_active_leads, overdue_follow_ups, conversions, average_response_time, lead_score_average, conversion_rate, average_deal_size, response_time_rank)
-- SELECT a.agent_id,
--        CURRENT_DATE,
--        (10 + floor(random()*40))::INT,                     -- 10–50 active leads
--        (floor(random()*10))::INT,                         -- 0–9 overdue
--        (floor(random()*15))::INT,                         -- 0–14 conversions
--        (floor(random()*6) || ' hours')::INTERVAL,         -- 0–5 hours avg response
--        (50 + floor(random()*30))::INT,                    -- average score 50–80
--        round((5 + random()*20)::NUMERIC, 2),              -- conversion rate 5–25%
--        (800000 + (random()*3000000))::NUMERIC(15,2),      -- deal size ~0.8–3.8M AED
--        (1 + floor(random()*10))::INT                      -- rank 1–10
-- FROM agents a;


-- Insert into lead_conversion_history respecting Rule 6
WITH lead_with_status_assignment AS (
    SELECT
        l.lead_id,
        ROW_NUMBER() OVER (ORDER BY random()) AS rn
    FROM leads l
    LIMIT 50
),
statuses AS (
    SELECT
        rn,
        (ARRAY['new','contacted','qualified','viewing_scheduled','negotiation'])[(rn % 5) + 1] AS previous_status
    FROM lead_with_status_assignment
)
INSERT INTO lead_conversion_history (lead_id, previous_status, new_status, notes)
SELECT
    lsa.lead_id,
    s.previous_status,
    CASE s.previous_status
        WHEN 'new' THEN 'contacted'
        WHEN 'contacted' THEN 'qualified'
        WHEN 'qualified' THEN 'viewing_scheduled'
        WHEN 'viewing_scheduled' THEN 'negotiation'
        WHEN 'negotiation' THEN (ARRAY['converted','lost'])[floor(random()*2)+1]
        ELSE s.previous_status
    END AS new_status,
    'Auto-generated valid status change'
FROM lead_with_status_assignment AS lsa
JOIN statuses AS s
ON lsa.rn = s.rn;

