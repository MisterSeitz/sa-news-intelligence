-- Migration: Add image_url to crime_intelligence.incidents
-- RequiAdded HeyGen APIred for the unified news view to display crime images.

ALTER TABLE crime_intelligence.incidents 
ADD COLUMN IF NOT EXISTS image_url text;

COMMENT ON COLUMN crime_intelligence.incidents.image_url IS 'URL of the main image associated with the incident report.';
