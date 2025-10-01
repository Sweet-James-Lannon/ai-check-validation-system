-- Add columns for tracking when checks are flagged for review
ALTER TABLE checks 
ADD COLUMN flagged_at timestamptz,
ADD COLUMN flagged_by text,
ADD COLUMN flagged_by_name text;

-- Add comment for documentation
COMMENT ON COLUMN checks.flagged_at IS 'Timestamp when check was flagged for manual review';
COMMENT ON COLUMN checks.flagged_by IS 'Username of person who flagged the check';
COMMENT ON COLUMN checks.flagged_by_name IS 'Display name of person who flagged the check';
