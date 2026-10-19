CREATE SCHEMA anovel_canon;
CREATE TABLE anovel_canon.schema_migrations (
    version integer PRIMARY KEY,
    checksum text NOT NULL,
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE anovel_canon.projects (project_id text PRIMARY KEY CHECK (length(project_id) BETWEEN 1 AND 200));
CREATE TABLE anovel_canon.branches (
    project_id text NOT NULL REFERENCES anovel_canon.projects(project_id),
    branch_id text NOT NULL CHECK (length(branch_id) BETWEEN 1 AND 200),
    head_id text,
    initializer text NOT NULL CHECK (length(initializer) BETWEEN 1 AND 200),
    authorization_version bigint NOT NULL DEFAULT 0 CHECK (authorization_version >= 0),
    enabled boolean NOT NULL DEFAULT true,
    PRIMARY KEY (project_id, branch_id)
);
CREATE TABLE anovel_canon.requests (
    project_id text NOT NULL, branch_id text NOT NULL, request_id text NOT NULL,
    actor text NOT NULL,
    authorization_version bigint NOT NULL CHECK (authorization_version >= 0),
    execution_version bigint NOT NULL DEFAULT 0 CHECK (execution_version >= 0),
    cancelled boolean NOT NULL DEFAULT false,
    PRIMARY KEY (project_id, branch_id, request_id),
    FOREIGN KEY (project_id, branch_id) REFERENCES anovel_canon.branches(project_id, branch_id)
);
CREATE TABLE anovel_canon.artifacts (
    project_id text NOT NULL, branch_id text NOT NULL,
    artifact_id text NOT NULL, artifact_type text NOT NULL CHECK (artifact_type IN ('ROOT_INPUT', 'RAW_PROSE', 'INITIALIZER_AUTHORITY')),
    encoding text NOT NULL CHECK (encoding IN ('ANOVELOS-CJSON-1', 'RAW-UTF8')),
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    content bytea NOT NULL,
    PRIMARY KEY (project_id, branch_id, artifact_id),
    UNIQUE (project_id, branch_id, artifact_id, artifact_type),
    FOREIGN KEY (project_id, branch_id) REFERENCES anovel_canon.branches(project_id, branch_id)
);
CREATE TABLE anovel_canon.commits (
    project_id text NOT NULL, branch_id text NOT NULL, commit_id text NOT NULL CHECK (commit_id ~ '^sha256:[0-9a-f]{64}$'),
    parent_id text, sequence bigint NOT NULL CHECK (sequence >= 0),
    request_id text NOT NULL, payload_hash text NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
    canonical_bytes bytea NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (project_id, branch_id, commit_id),
    UNIQUE (project_id, branch_id, sequence),
    UNIQUE (project_id, branch_id, request_id),
    UNIQUE (project_id, branch_id, request_id, commit_id, payload_hash),
    FOREIGN KEY (project_id, branch_id) REFERENCES anovel_canon.branches(project_id, branch_id),
    FOREIGN KEY (project_id, branch_id, parent_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id),
    FOREIGN KEY (project_id, branch_id, request_id) REFERENCES anovel_canon.requests(project_id, branch_id, request_id),
    CHECK ((parent_id IS NULL AND sequence = 0) OR (parent_id IS NOT NULL AND sequence > 0))
);
CREATE UNIQUE INDEX one_root_per_branch ON anovel_canon.commits(project_id, branch_id) WHERE parent_id IS NULL;
ALTER TABLE anovel_canon.branches ADD CONSTRAINT scoped_head FOREIGN KEY (project_id, branch_id, head_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id);
CREATE TABLE anovel_canon.commit_artifacts (
    project_id text NOT NULL, branch_id text NOT NULL, commit_id text NOT NULL,
    artifact_id text NOT NULL, artifact_type text NOT NULL,
    PRIMARY KEY (project_id, branch_id, commit_id, artifact_type),
    FOREIGN KEY (project_id, branch_id, commit_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id),
    FOREIGN KEY (project_id, branch_id, artifact_id, artifact_type) REFERENCES anovel_canon.artifacts(project_id, branch_id, artifact_id, artifact_type)
);
CREATE TABLE anovel_canon.events (
    project_id text NOT NULL, branch_id text NOT NULL, commit_id text NOT NULL,
    event_type text NOT NULL CHECK (event_type = 'ROOT_INITIALIZED'),
    reducer_version text NOT NULL CHECK (reducer_version = 'ROOT-1'),
    PRIMARY KEY (project_id, branch_id, commit_id),
    FOREIGN KEY (project_id, branch_id, commit_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id)
);
CREATE TABLE anovel_canon.receipts (
    project_id text NOT NULL, branch_id text NOT NULL, request_id text NOT NULL,
    commit_id text NOT NULL, payload_hash text NOT NULL,
    PRIMARY KEY (project_id, branch_id, request_id),
    FOREIGN KEY (project_id, branch_id, request_id, commit_id, payload_hash) REFERENCES anovel_canon.commits(project_id, branch_id, request_id, commit_id, payload_hash)
);
CREATE TABLE anovel_canon.entities (
    project_id text NOT NULL, branch_id text NOT NULL, entity_id text NOT NULL,
    commit_id text NOT NULL,
    PRIMARY KEY (project_id, branch_id, entity_id),
    FOREIGN KEY (project_id, branch_id, commit_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id)
);
CREATE TABLE anovel_canon.relationships (
    project_id text NOT NULL, branch_id text NOT NULL, relationship_id text NOT NULL,
    party_a text NOT NULL, party_b text NOT NULL, commit_id text NOT NULL,
    PRIMARY KEY (project_id, branch_id, relationship_id),
    FOREIGN KEY (project_id, branch_id, party_a) REFERENCES anovel_canon.entities(project_id, branch_id, entity_id),
    FOREIGN KEY (project_id, branch_id, party_b) REFERENCES anovel_canon.entities(project_id, branch_id, entity_id),
    FOREIGN KEY (project_id, branch_id, commit_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id)
);
CREATE TABLE anovel_canon.facts (
    project_id text NOT NULL, branch_id text NOT NULL, fact_id text NOT NULL,
    subject_id text NOT NULL, commit_id text NOT NULL,
    PRIMARY KEY (project_id, branch_id, fact_id),
    FOREIGN KEY (project_id, branch_id, subject_id) REFERENCES anovel_canon.entities(project_id, branch_id, entity_id),
    FOREIGN KEY (project_id, branch_id, commit_id) REFERENCES anovel_canon.commits(project_id, branch_id, commit_id)
);
CREATE FUNCTION anovel_canon.reject_history_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'accepted Canon history is immutable' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER immutable_artifacts BEFORE UPDATE OR DELETE ON anovel_canon.artifacts FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_commits BEFORE UPDATE OR DELETE ON anovel_canon.commits FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_links BEFORE UPDATE OR DELETE ON anovel_canon.commit_artifacts FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_events BEFORE UPDATE OR DELETE ON anovel_canon.events FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_receipts BEFORE UPDATE OR DELETE ON anovel_canon.receipts FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_entities BEFORE UPDATE OR DELETE ON anovel_canon.entities FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_relationships BEFORE UPDATE OR DELETE ON anovel_canon.relationships FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
CREATE TRIGGER immutable_facts BEFORE UPDATE OR DELETE ON anovel_canon.facts FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_history_change();
REVOKE ALL ON ALL TABLES IN SCHEMA anovel_canon FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA anovel_canon FROM PUBLIC;
