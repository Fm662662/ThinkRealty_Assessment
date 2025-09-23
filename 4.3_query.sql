-- 4.3 Agent Workload Optimization Query

-- Current workload distribution (active leads per agent)
WITH workload_distribution AS (
    SELECT a.agent_id, a.full_name,
           COUNT(*) FILTER (WHERE l.status NOT IN ('converted','lost')) AS active_leads
    FROM agents a
    LEFT JOIN lead_assignments la ON a.agent_id = la.agent_id AND la.reassigned = FALSE
    LEFT JOIN leads l ON la.lead_id = l.lead_id
    GROUP BY a.agent_id, a.full_name
),

-- Agents approaching maximum capacity (>=45 active leads)
agents_near_capacity AS (
    SELECT * FROM workload_distribution
    WHERE active_leads >= 45
),

-- Specialized vs general agent performance (conversion rate comparison)
specialization_perf AS (
    SELECT a.agent_id, a.full_name,
           CASE WHEN a.specialization IS NOT NULL AND a.specialization <> '' 
                THEN 'specialized' ELSE 'general' END AS agent_type,
           COUNT(*) FILTER (WHERE l.status = 'converted')::float / NULLIF(COUNT(*),0) * 100 AS conversion_rate,
           COUNT(*) AS total_leads
    FROM agents a
    LEFT JOIN lead_assignments la ON a.agent_id = la.agent_id AND la.reassigned = FALSE
    LEFT JOIN leads l ON la.lead_id = l.lead_id
    GROUP BY a.agent_id, a.full_name, agent_type
),

-- Lead response time correlation with conversion
response_time_corr AS (
    SELECT l.lead_id, la.agent_id, l.status,
           EXTRACT(EPOCH FROM (MIN(a.created_at) - l.created_at))/3600 AS hours_to_first_response
    FROM leads l
    JOIN lead_assignments la ON l.lead_id = la.lead_id AND la.reassigned = FALSE
    JOIN lead_activities a ON l.lead_id = a.lead_id
    GROUP BY l.lead_id, la.agent_id, l.status, l.created_at
)

-- Final output (combined view)
SELECT 'workload_distribution' AS category, row_to_json(workload_distribution) AS data
FROM workload_distribution
UNION ALL
SELECT 'agents_near_capacity' AS category, row_to_json(agents_near_capacity) AS data
FROM agents_near_capacity
UNION ALL
SELECT 'specialization_perf' AS category, row_to_json(specialization_perf) AS data
FROM specialization_perf
UNION ALL
SELECT 'response_time_corr' AS category, row_to_json(response_time_corr) AS data
FROM response_time_corr;
