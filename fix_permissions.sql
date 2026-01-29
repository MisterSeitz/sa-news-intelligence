-- Grant sequence permissions for the existing motoring_id_seq and any others
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai_intelligence TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai_intelligence TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai_intelligence TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai_intelligence TO authenticated;

-- Specifically ensure the motoring sequence is covered (if it's not following standard naming or if schema default grants missed it)
-- We can dynamically find sequences but the ALL SEQUENCES ABOVE usually works for existing ones.
-- To be safe for future tables, we can alter default privileges.

ALTER DEFAULT PRIVILEGES IN SCHEMA ai_intelligence GRANT USAGE, SELECT ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_intelligence GRANT USAGE, SELECT ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_intelligence GRANT USAGE, SELECT ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_intelligence GRANT USAGE, SELECT ON SEQUENCES TO authenticated;
