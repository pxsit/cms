BEGIN;
ALTER TABLE tasks ADD COLUMN is_notice boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN restricted boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ALTER COLUMN is_notice DROP DEFAULT;
ALTER TABLE tasks ALTER COLUMN restricted DROP DEFAULT;
CREATE TABLE task_allowed_users (
    task_id integer NOT NULL REFERENCES tasks(id) ON UPDATE CASCADE ON DELETE CASCADE,
    user_id integer NOT NULL REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (task_id, user_id)
);
COMMIT;
