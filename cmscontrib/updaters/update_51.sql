BEGIN;
-- IF NOT EXISTS also supports installations previously using add-counter.
ALTER TABLE contests ADD COLUMN IF NOT EXISTS show_task_scores_in_overview boolean NOT NULL DEFAULT true;
ALTER TABLE contests ADD COLUMN IF NOT EXISTS show_task_scores_in_sidebar boolean NOT NULL DEFAULT true;
ALTER TABLE contests ALTER COLUMN show_task_scores_in_overview DROP DEFAULT;
ALTER TABLE contests ALTER COLUMN show_task_scores_in_sidebar DROP DEFAULT;
COMMIT;
