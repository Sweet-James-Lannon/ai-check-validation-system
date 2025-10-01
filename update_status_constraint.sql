-- Drop the existing check constraint
ALTER TABLE checks DROP CONSTRAINT IF EXISTS checks_status_check;

-- Add a new constraint that includes needs_review
ALTER TABLE checks ADD CONSTRAINT checks_status_check 
CHECK (status IN ('pending', 'needs_review', 'approved', 'rejected'));

-- Verify the constraint was added
SELECT conname, consrc 
FROM pg_constraint 
WHERE conrelid = 'checks'::regclass 
AND conname = 'checks_status_check';
