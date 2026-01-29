-- Align 'motoring' table with standard Niche Intelligence Schema
ALTER TABLE ai_intelligence.motoring ADD COLUMN IF NOT EXISTS country text;
ALTER TABLE ai_intelligence.motoring ADD COLUMN IF NOT EXISTS city text;
ALTER TABLE ai_intelligence.motoring ADD COLUMN IF NOT EXISTS location text;
ALTER TABLE ai_intelligence.motoring ADD COLUMN IF NOT EXISTS is_south_africa boolean DEFAULT false;
ALTER TABLE ai_intelligence.motoring ADD COLUMN IF NOT EXISTS niche text;

-- Ensure URL constraint for Upsert
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'motoring_url_key') THEN
        ALTER TABLE ai_intelligence.motoring ADD CONSTRAINT motoring_url_key UNIQUE (url);
    END IF;
END;
$$;
