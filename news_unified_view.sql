-- Unified News View for Visita Intelligence
-- Aggregates data from general news, crime incidents, sports, and politics into a single queryable view.

CREATE OR REPLACE VIEW news_unified_view AS

-- 1. General News (ai_intelligence.entries)
SELECT 
    id,
    title,
    summary,
    content,
    published_date as published_at,
    CASE 
        WHEN canonical_url IS NOT NULL THEN canonical_url
        ELSE (data->>'url') 
    END as source_url,
    (data->>'image_url') as image_url,
    category,
    sentiment_label as sentiment,
    COALESCE(sentiment_score, 0) as sentiment_score,
    'general' as origin_type,
    'ai_intelligence.entries' as origin_table,
    created_at
FROM ai_intelligence.entries

UNION ALL

-- 2. Crime Incidents (crime_intelligence.incidents)
SELECT 
    id,
    title,
    description as summary,
    full_text as content,
    published_at,
    source_url,
    image_url, -- Ensure this column exists or use NULL if not yet added to schema
    type as category,
    CASE 
        WHEN severity_level >= 3 THEN 'High Urgency'
        WHEN severity_level = 2 THEN 'Moderate Urgency'
        ELSE 'Low Urgency'
    END as sentiment,
    (severity_level * 3.33) as sentiment_score, -- Normalize 1-3 to roughly 0-10 scale
    'crime' as origin_type,
    'crime_intelligence.incidents' as origin_table,
    created_at
FROM crime_intelligence.incidents

UNION ALL

-- 3. Election News (gov_intelligence.election_news)
SELECT 
    id,
    title,
    summary,
    content,
    published_at,
    source_url,
    image_url,
    'Politics' as category,
    sentiment,
    0 as sentiment_score, -- Needs calculation or mapping if needed
    'politics' as origin_type,
    'gov_intelligence.election_news' as origin_table,
    created_at
FROM gov_intelligence.election_news

UNION ALL

-- 4. Sports News (sports_intelligence.news)
SELECT 
    id,
    title,
    summary,
    NULL as content, -- Sports news often lacks full content in this table
    published_at,
    url as source_url,
    (structured_data->>'image_url') as image_url,
    category,
    (structured_data->>'sentiment_label') as sentiment,
    sentiment_score,
    'sports' as origin_type,
    'sports_intelligence.news' as origin_table,
    created_at
FROM sports_intelligence.news;

-- Permissions (Adjust as needed)
GRANT SELECT ON news_unified_view TO authenticated;
GRANT SELECT ON news_unified_view TO service_role;
