-- 4.1 Lead Performance Analytics Report

-- 1. Lead conversion rates by source and agent
SELECT 
    ls.source_type,
    a.full_name AS agent_name,
    COUNT(l.lead_id) FILTER (WHERE l.status = 'converted')::decimal / NULLIF(COUNT(l.lead_id),0) * 100 AS conversion_rate
FROM leads l
JOIN lead_sources ls ON l.lead_id = ls.lead_id
JOIN lead_assignments la ON l.lead_id = la.lead_id AND la.reassigned = FALSE
JOIN agents a ON la.agent_id = a.agent_id
GROUP BY ls.source_type, a.full_name
ORDER BY conversion_rate DESC;


-- 2. Average time to conversion by property type
SELECT 
    l.property_type,
    AVG(EXTRACT(EPOCH FROM (ch.changed_at - l.created_at)) / 86400)::numeric(10,2) AS avg_days_to_convert
FROM lead_conversion_history ch
JOIN leads l ON ch.lead_id = l.lead_id
WHERE ch.new_status = 'converted'
GROUP BY l.property_type
ORDER BY avg_days_to_convert;


-- 3. Monthly lead volume trends
SELECT 
    DATE_TRUNC('month', l.created_at) AS month,
    COUNT(*) AS lead_count,
    COUNT(*) FILTER (WHERE l.status = 'converted') AS converted_count
FROM leads l
GROUP BY month
ORDER BY month;


-- 4. Agent performance rankings
SELECT 
    a.agent_id,
    a.full_name,
    COUNT(l.lead_id) FILTER (WHERE l.status = 'converted') AS total_converted,
    AVG(EXTRACT(EPOCH FROM (ch.changed_at - l.created_at)) / 86400) AS avg_days_to_convert,
    COUNT(DISTINCT l.lead_id) AS total_leads
FROM agents a
LEFT JOIN lead_assignments la ON a.agent_id = la.agent_id AND la.reassigned = FALSE
LEFT JOIN leads l ON la.lead_id = l.lead_id
LEFT JOIN lead_conversion_history ch ON l.lead_id = ch.lead_id AND ch.new_status = 'converted'
GROUP BY a.agent_id, a.full_name
ORDER BY total_converted DESC NULLS LAST;


-- 5. Revenue attribution by lead source
-- Assuming leads table has "deal_value" column populated for converted leads
SELECT 
    ls.source_type,
    SUM(l.deal_value) AS total_revenue,
    AVG(l.deal_value) AS avg_deal_value,
    COUNT(*) FILTER (WHERE l.status = 'converted') AS converted_leads
FROM leads l
JOIN lead_sources ls ON l.lead_id = ls.lead_id
WHERE l.status = 'converted'
GROUP BY ls.source_type
ORDER BY total_revenue DESC;
