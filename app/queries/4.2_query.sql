-- 4.2 Lead Quality Analysis Query

-- High-scoring leads that did not convert
WITH high_score_not_converted AS (
    SELECT l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id
    FROM leads l
    JOIN lead_sources ls ON l.lead_id = ls.lead_id
    JOIN lead_assignments la ON l.lead_id = la.lead_id
    WHERE l.lead_score >= 80
      AND l.status NOT IN ('converted')
),

-- Low-scoring leads that converted
low_score_converted AS (
    SELECT l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id
    FROM leads l
    JOIN lead_sources ls ON l.lead_id = ls.lead_id
    JOIN lead_assignments la ON l.lead_id = la.lead_id
    WHERE l.lead_score <= 40
      AND l.status = 'converted'
),

-- Source quality comparison over time (monthly conversion rate by source)
source_quality AS (
    SELECT 
        ls.source_type,
        DATE_TRUNC('month', l.created_at) AS month,
        COUNT(*) FILTER (WHERE l.status = 'converted')::float / COUNT(*) * 100 AS conversion_rate,
        COUNT(*) AS total_leads
    FROM leads l
    JOIN lead_sources ls ON l.lead_id = ls.lead_id
    GROUP BY ls.source_type, DATE_TRUNC('month', l.created_at)
    ORDER BY month
),

-- Optimal follow-up timing (avg hours between lead creation and first completed follow-up, by conversion outcome)
followup_timing AS (
    SELECT 
        l.status,
        ROUND(AVG(EXTRACT(EPOCH FROM (f.completed_at - l.created_at)) / 3600), 2) AS avg_hours_to_first_followup
    FROM leads l
    JOIN follow_up_tasks f ON l.lead_id = f.lead_id
    WHERE f.completed = TRUE
    GROUP BY l.status
)

-- Final Output (make all SELECTs have same number of columns)
SELECT
    'high_score_not_converted' AS category,
    l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id,
    NULL::text AS avg_hours_to_first_followup,
    NULL::text AS total_leads
FROM high_score_not_converted l
JOIN lead_sources ls ON l.lead_id = ls.lead_id
JOIN lead_assignments la ON l.lead_id = la.lead_id

UNION ALL

SELECT
    'low_score_converted' AS category,
    l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id,
    NULL::text AS avg_hours_to_first_followup,
    NULL::text AS total_leads
FROM low_score_converted l
JOIN lead_sources ls ON l.lead_id = ls.lead_id
JOIN lead_assignments la ON l.lead_id = la.lead_id

UNION ALL

SELECT
    'source_quality' AS category,
    NULL::uuid AS lead_id,
    NULL::int AS lead_score,
    NULL::text AS status,
    sq.source_type,
    NULL::uuid AS agent_id,
    sq.conversion_rate::text AS avg_hours_to_first_followup,
    sq.total_leads::text AS total_leads
FROM source_quality sq

UNION ALL

SELECT
    'followup_timing' AS category,
    NULL::uuid AS lead_id,
    NULL::int AS lead_score,
    ft.status,
    NULL::text AS source_type,
    NULL::uuid AS agent_id,
    ft.avg_hours_to_first_followup::text AS avg_hours_to_first_followup,
    NULL::text AS total_leads
FROM followup_timing ft;



------------------IT WOULD GIVE REPORT IN SINGLE JSON FORMAT---------------------------


-- SELECT json_build_object(
--     'high_score_not_converted', h.high_score_not_converted,
--     'low_score_converted', lc.low_score_converted,
--     'source_quality', sq.source_quality,
--     'followup_timing', ft.followup_timing
-- ) AS lead_quality_report
-- FROM
--     -- High-scoring leads that did not convert
--     (SELECT json_agg(row_to_json(h)) AS high_score_not_converted
--      FROM (
--          SELECT l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id
--          FROM leads l
--          JOIN lead_sources ls ON l.lead_id = ls.lead_id
--          JOIN lead_assignments la ON l.lead_id = la.lead_id
--          WHERE l.lead_score >= 80 AND l.status != 'converted'
--      ) h) h,
     
--     -- Low-scoring leads that converted
--     (SELECT json_agg(row_to_json(lc)) AS low_score_converted
--      FROM (
--          SELECT l.lead_id, l.lead_score, l.status, ls.source_type, la.agent_id
--          FROM leads l
--          JOIN lead_sources ls ON l.lead_id = ls.lead_id
--          JOIN lead_assignments la ON l.lead_id = la.lead_id
--          WHERE l.lead_score <= 40 AND l.status = 'converted'
--      ) lc) lc,
     
--     -- Source quality comparison over time
--     (SELECT json_agg(row_to_json(sq)) AS source_quality
--      FROM (
--          SELECT ls.source_type,
--                 DATE_TRUNC('month', l.created_at) AS month,
--                 COUNT(*) FILTER (WHERE l.status='converted')::float/COUNT(*)*100 AS conversion_rate,
--                 COUNT(*) AS total_leads
--          FROM leads l
--          JOIN lead_sources ls ON l.lead_id = ls.lead_id
--          GROUP BY ls.source_type, DATE_TRUNC('month', l.created_at)
--      ) sq) sq,
     
--     -- Optimal follow-up timing analysis
--     (SELECT json_agg(row_to_json(ft)) AS followup_timing
--      FROM (
--          SELECT l.status,
--                 ROUND(AVG(EXTRACT(EPOCH FROM (f.completed_at - l.created_at))/3600),2) AS avg_hours_to_first_followup
--          FROM leads l
--          JOIN follow_up_tasks f ON l.lead_id = f.lead_id
--          WHERE f.completed = TRUE
--          GROUP BY l.status
--      ) ft) ft;
