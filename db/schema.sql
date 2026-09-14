-- Plain-SQL mirror of backend/alembic/versions/0001_initial_schema.py
-- Provided for quick review; the Alembic migration is the source of truth.
-- Target: PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'officer',  -- admin | officer | auditor
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deactivated_at  TIMESTAMPTZ
);
CREATE INDEX ix_users_email ON users(email);

CREATE TABLE camera_feeds (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    source_type     VARCHAR(32)  NOT NULL,   -- rtsp | file | upload
    source_uri      VARCHAR(1024) NOT NULL,
    location_label  VARCHAR(255),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    target_fps      INTEGER NOT NULL DEFAULT 15,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE risk_zones (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id             UUID NOT NULL REFERENCES camera_feeds(id) ON DELETE CASCADE,
    name                  VARCHAR(255) NOT NULL,
    polygon               JSONB NOT NULL,     -- [[x,y], ...] normalised 0-1 frame coords
    safe_distance_meters  DOUBLE PRECISION NOT NULL DEFAULT 3.0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_versions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(128) NOT NULL,
    weights_path  VARCHAR(1024) NOT NULL,
    trained_on    VARCHAR(255),
    map50         DOUBLE PRECISION,           -- mAP@0.5, target >= 0.75 per NFR-02
    map50_95      DOUBLE PRECISION,
    is_active     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE detection_events (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id             UUID NOT NULL REFERENCES camera_feeds(id) ON DELETE CASCADE,
    zone_id               UUID REFERENCES risk_zones(id) ON DELETE SET NULL,
    track_id              INTEGER NOT NULL,
    timestamp             TIMESTAMPTZ NOT NULL DEFAULT now(),
    confidence            DOUBLE PRECISION NOT NULL,
    bbox                  JSONB NOT NULL,      -- {x1,y1,x2,y2} normalised
    distance_estimate_m   DOUBLE PRECISION,
    closing_speed_mps     DOUBLE PRECISION,
    classification        VARCHAR(16) NOT NULL,  -- safe | caution | critical
    model_version         VARCHAR(64) NOT NULL
);
CREATE INDEX ix_detection_events_timestamp ON detection_events(timestamp);
CREATE INDEX ix_detection_events_camera_id ON detection_events(camera_id);
CREATE INDEX ix_detection_events_classification ON detection_events(classification);

CREATE TABLE alerts (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    detection_event_id      UUID NOT NULL REFERENCES detection_events(id) ON DELETE CASCADE,
    severity                 VARCHAR(16) NOT NULL,   -- caution | critical
    message                  VARCHAR(500) NOT NULL,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged              BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by           UUID REFERENCES users(id),
    dispatched_to_external    BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_alerts_created_at ON alerts(created_at);
CREATE INDEX ix_alerts_severity ON alerts(severity);

CREATE TABLE alert_rules (
    id                                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id                         UUID REFERENCES camera_feeds(id) ON DELETE CASCADE,  -- NULL = global default
    confidence_threshold              DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    low_light_confidence_threshold    DOUBLE PRECISION NOT NULL DEFAULT 0.4,
    safe_distance_meters              DOUBLE PRECISION NOT NULL DEFAULT 3.0,
    closing_speed_critical_mps        DOUBLE PRECISION NOT NULL DEFAULT 2.0,
    updated_at                        TIMESTAMPTZ NOT NULL DEFAULT now()
);
