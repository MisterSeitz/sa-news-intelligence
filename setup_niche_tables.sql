-- Create Schema (if strictly needed, though 'ai_intelligence' likely exists)
CREATE SCHEMA IF NOT EXISTS ai_intelligence;

-- Function to create the standard table structure for a niche
CREATE OR REPLACE FUNCTION ai_intelligence.create_niche_table(table_name text)
RETURNS void AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS ai_intelligence.%I (
            url text PRIMARY KEY,
            niche text,
            source_feed text,
            title text,
            published text,
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

-- Initialize Tables for all Niches
SELECT ai_intelligence.create_niche_table('gaming');
SELECT ai_intelligence.create_niche_table('crypto');
SELECT ai_intelligence.create_niche_table('tech');
SELECT ai_intelligence.create_niche_table('nuclear');
SELECT ai_intelligence.create_niche_table('education');
SELECT ai_intelligence.create_niche_table('foodtech');
SELECT ai_intelligence.create_niche_table('health');
SELECT ai_intelligence.create_niche_table('nutrition');
SELECT ai_intelligence.create_niche_table('luxury');
SELECT ai_intelligence.create_niche_table('realestate');
SELECT ai_intelligence.create_niche_table('retail');
SELECT ai_intelligence.create_niche_table('social');
SELECT ai_intelligence.create_niche_table('vc');
SELECT ai_intelligence.create_niche_table('web3');
SELECT ai_intelligence.create_niche_table('general');
SELECT ai_intelligence.create_niche_table('energy');
