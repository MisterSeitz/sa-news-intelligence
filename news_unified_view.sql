-- Create a Unified View for News Intelligence
-- Aggregates data from:
-- 1. crime_intelligence.incidents
-- 2. ai_intelligence.entries (General News)
-- 3. gov_intelligence.election_news
-- 4. sports_intelligence.news

create or replace view public.news_unified_view as

-- 1. Crime Intelligence
select 
    id::text as id,
    title,
    summary,
    created_at as published_at,
    source as source_url,
    data->>'image_url' as image_url,
    'Crime' as category,
    'High Urgency' as sentiment, -- Default for crime
    severity as risk_level,
    'crime_intelligence.incidents' as origin_table
from crime_intelligence.incidents

union all

-- 2. General News (Entries)
select 
    id::text as id,
    title,
    summary,
    published_date as published_at,
    url as source_url,
    data->>'image_url' as image_url,
    category,
    sentiment_label as sentiment,
    'Info' as risk_level,
    'ai_intelligence.entries' as origin_table
from ai_intelligence.entries
where category != 'Crime' -- Avoid duplicates if crime is double-logged

union all

-- 3. Election News
select 
    id::text as id,
    title,
    summary,
    published_at,
    url as source_url,
    image_url,
    'Politics' as category,
    sentiment,
    'Info' as risk_level,
    'gov_intelligence.election_news' as origin_table
from gov_intelligence.election_news

union all

-- 4. Sports News
select 
    id::text as id,
    title,
    summary,
    published_at,
    url as source_url,
    structured_data->>'image_url' as image_url,
    'Sports' as category,
    case 
        when sentiment_score > 7 then 'High Excitement' 
        else 'General' 
    end as sentiment,
    'Info' as risk_level,
    'sports_intelligence.news' as origin_table
from sports_intelligence.news;

-- Permissions
grant select on public.news_unified_view to authenticated;
grant select on public.news_unified_view to anon;
grant select on public.news_unified_view to service_role;
