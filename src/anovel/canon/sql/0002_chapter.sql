-- Incremental chapter protocol. Never rewrite 0001 or accepted root bytes.
ALTER TABLE anovel_canon.requests ADD COLUMN purpose text NOT NULL DEFAULT 'ROOT'
    CHECK (purpose IN ('ROOT','CHAPTER'));
ALTER TABLE anovel_canon.requests ADD COLUMN expected_parent text;
ALTER TABLE anovel_canon.requests ADD CONSTRAINT request_parent_scope
    FOREIGN KEY(project_id,branch_id,expected_parent)
    REFERENCES anovel_canon.commits(project_id,branch_id,commit_id);
ALTER TABLE anovel_canon.requests ADD CONSTRAINT request_purpose_parent
    CHECK ((purpose='ROOT' AND expected_parent IS NULL) OR
           (purpose='CHAPTER' AND expected_parent IS NOT NULL));

ALTER TABLE anovel_canon.artifacts DROP CONSTRAINT artifacts_artifact_type_check;
ALTER TABLE anovel_canon.artifacts ADD CONSTRAINT artifacts_artifact_type_check CHECK
    (artifact_type IN ('ROOT_INPUT','RAW_PROSE','INITIALIZER_AUTHORITY',
     'CHAPTER_INPUT','NARRATIVE_DELTA','DEPENDENCY_BUNDLE','COMMIT_PERMIT','STATE_SNAPSHOT'));
ALTER TABLE anovel_canon.events DROP CONSTRAINT events_event_type_check;
ALTER TABLE anovel_canon.events DROP CONSTRAINT events_reducer_version_check;
ALTER TABLE anovel_canon.events ADD CONSTRAINT event_reducer_pair CHECK
    ((event_type='ROOT_INITIALIZED' AND reducer_version='ROOT-1') OR
     (event_type='CHAPTER_COMMITTED' AND reducer_version='FACT_DELTA-1'));

CREATE TABLE anovel_canon.chapter_authorities (
    project_id text NOT NULL, branch_id text NOT NULL,
    actor text NOT NULL, issuer_id text NOT NULL,
    version bigint NOT NULL CHECK(version>=0), enabled boolean NOT NULL,
    profile text NOT NULL CHECK(profile='ISOLATED_TEST'),
    policy_hash text NOT NULL CHECK(policy_hash ~ '^[0-9a-f]{64}$'),
    policy_bytes bytea NOT NULL,
    PRIMARY KEY(project_id,branch_id),
    FOREIGN KEY(project_id,branch_id) REFERENCES anovel_canon.branches(project_id,branch_id)
);
CREATE TABLE anovel_canon.commit_permits (
    project_id text NOT NULL, branch_id text NOT NULL, permit_ref text NOT NULL,
    request_id text NOT NULL, actor text NOT NULL, parent_id text NOT NULL,
    payload_hash text NOT NULL CHECK(payload_hash ~ '^[0-9a-f]{64}$'),
    issuer_id text NOT NULL,
    authority_version bigint NOT NULL CHECK(authority_version>=0),
    execution_version bigint NOT NULL CHECK(execution_version>=0),
    policy_hash text NOT NULL CHECK(policy_hash ~ '^[0-9a-f]{64}$'),
    expires_at timestamptz NOT NULL,
    content_hash text NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
    content bytea NOT NULL, revoked boolean NOT NULL DEFAULT false,
    PRIMARY KEY(project_id,branch_id,permit_ref),
    FOREIGN KEY(project_id,branch_id,request_id)
        REFERENCES anovel_canon.requests(project_id,branch_id,request_id),
    FOREIGN KEY(project_id,branch_id,parent_id)
        REFERENCES anovel_canon.commits(project_id,branch_id,commit_id)
);
CREATE FUNCTION anovel_canon.guard_permit_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'permit evidence cannot be deleted' USING ERRCODE='23514';
    END IF;
    IF OLD.revoked OR NOT NEW.revoked OR
       ROW(OLD.project_id,OLD.branch_id,OLD.permit_ref,OLD.request_id,OLD.actor,
           OLD.parent_id,OLD.payload_hash,OLD.issuer_id,OLD.authority_version,
           OLD.execution_version,OLD.policy_hash,OLD.expires_at,OLD.content_hash,OLD.content)
       IS DISTINCT FROM
       ROW(NEW.project_id,NEW.branch_id,NEW.permit_ref,NEW.request_id,NEW.actor,
           NEW.parent_id,NEW.payload_hash,NEW.issuer_id,NEW.authority_version,
           NEW.execution_version,NEW.policy_hash,NEW.expires_at,NEW.content_hash,NEW.content)
    THEN
        RAISE EXCEPTION 'permit evidence is immutable; revocation is monotone' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER immutable_permit BEFORE UPDATE OR DELETE ON anovel_canon.commit_permits
    FOR EACH ROW EXECUTE FUNCTION anovel_canon.guard_permit_history();
REVOKE ALL ON anovel_canon.chapter_authorities,anovel_canon.commit_permits FROM PUBLIC;
REVOKE ALL ON FUNCTION anovel_canon.guard_permit_history() FROM PUBLIC;
