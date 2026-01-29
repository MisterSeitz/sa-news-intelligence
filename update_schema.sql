-- 1. Add image_url to all existing tables (if missing)
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ai_intelligence'
    LOOP
        EXECUTE format('ALTER TABLE ai_intelligence.%I ADD COLUMN IF NOT EXISTS image_url text;', t);
    END LOOP;
END;
$$;

-- 2. Update the create_niche_table function to include new columns for future tables
CREATE OR REPLACE FUNCTION ai_intelligence.create_niche_table(table_name text)
RETURNS void AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS ai_intelligence.%I (
            url text PRIMARY KEY,
            niche text,
            source_feed text,
            title text,
            published text, -- Keeping as text for flexibility, though timestamptz is better
            method text,
            sentiment text,
            category text,
            key_entities text[],
            ai_summary text,
            location text,
            city text,
            country text,
            is_south_africa boolean DEFAULT false,
            raw_context_source text,
            image_url text, -- Added
            
            -- Gaming
            game_studio text,
            game_genre text,
            platform text[],
            release_status text,
            
            -- Real Estate
            property_type text,
            listing_price text,
            sqft text,
            market_status text,
            
            -- VC / Startup
            company_name text,
            round_type text,
            funding_amount text,
            investor_list text[],
            
            -- Crypto
            token_symbol text,
            market_trend text,
            regulatory_impact text,
            
            -- Energy
            energy_type text,
            infrastructure_project text,
            capacity text,
            status text,

            -- Motoring (New)
            vehicle_make text,
            vehicle_model text,
            vehicle_type text,
            price_range text,
            
            created_at timestamptz DEFAULT now()
        );

        -- 1. Enable RLS
        ALTER TABLE ai_intelligence.%I ENABLE ROW LEVEL SECURITY;

        -- 2. Grants
        GRANT ALL ON ai_intelligence.%I TO service_role;
        GRANT SELECT ON ai_intelligence.%I TO anon, authenticated, postgres;

        -- 3. Policies
        DROP POLICY IF EXISTS "Public read %s" ON ai_intelligence.%I;
        CREATE POLICY "Public read %s" ON ai_intelligence.%I FOR SELECT USING (true);

        DROP POLICY IF EXISTS "Service write %s" ON ai_intelligence.%I;
        CREATE POLICY "Service write %s" ON ai_intelligence.%I FOR ALL TO service_role USING (true) WITH CHECK (true);
    ', 
    table_name, 
    table_name, 
    table_name, table_name, 
    table_name, table_name, table_name, table_name,
    table_name, table_name, table_name, table_name
    );
END;
$$ LANGUAGE plpgsql;

-- 3. Create 'motoring' table
SELECT ai_intelligence.create_niche_table('motoring');

-- 4. Backfill existing tables with new columns if they were created before the function update
-- (The loop above handled image_url, but we need to ensure Motoring columns exist if we ever decide to reuse tables or if Motoring was created with old function)
-- Since Motoring is new, it should be fine. But let's be safe and add Motoring columns to ALL tables just in case we switch niches mid-stream (like the 're-routing' logic does).
-- If we re-route a motoring article to 'luxury', 'luxury' table needs motoring columns? 
-- Ideally yes, effectively making all tables identical structure (Sparse Wide Table pattern).

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ai_intelligence'
    LOOP
        EXECUTE format('ALTER TABLE ai_intelligence.%I ADD COLUMN IF NOT EXISTS vehicle_make text;', t);
        EXECUTE format('ALTER TABLE ai_intelligence.%I ADD COLUMN IF NOT EXISTS vehicle_model text;', t);
        EXECUTE format('ALTER TABLE ai_intelligence.%I ADD COLUMN IF NOT EXISTS vehicle_type text;', t);
        EXECUTE format('ALTER TABLE ai_intelligence.%I ADD COLUMN IF NOT EXISTS price_range text;', t);
    END LOOP;
END;
$$;
