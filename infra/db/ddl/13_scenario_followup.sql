-- ============================================================================
-- scenario_followup —— 场景001 在线随访。
-- 管理出院/慢病患者的随访计划与记录，复用 platform_patient（不自存患者表）。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS scenario_followup;
SET search_path TO scenario_followup;

-- ---- 随访计划 --------------------------------------------------------------
CREATE TABLE followup_plan (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_no       varchar(32) NOT NULL UNIQUE,
    patient_id    varchar(64) NOT NULL,
    dept_code     varchar(32) NOT NULL,
    plan_type     varchar(16) NOT NULL DEFAULT 'chronic',   -- chronic/discharge/cancer
    interval_days integer     NOT NULL DEFAULT 30,
    start_date    date        NOT NULL,
    end_date      date,
    note          varchar(256),
    -- 公共字段
    org_id       varchar(32) NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    created_by   varchar(64) NOT NULL DEFAULT '',
    updated_by   varchar(64) NOT NULL DEFAULT '',
    is_deleted   boolean     NOT NULL DEFAULT false,
    row_version  integer     NOT NULL DEFAULT 0
);

-- ---- 随访记录 --------------------------------------------------------------
CREATE TABLE followup_record (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_no       varchar(32) REFERENCES followup_plan(plan_no),
    patient_id    varchar(64) NOT NULL,
    dept_code     varchar(32) NOT NULL,
    visit_date    date        NOT NULL,
    method        varchar(16) NOT NULL DEFAULT 'phone',   -- phone/video/onsite
    note          varchar(512),
    next_date     date,
    doctor_id     varchar(64),
    -- 公共字段
    org_id       varchar(32) NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    created_by   varchar(64) NOT NULL DEFAULT '',
    updated_by   varchar(64) NOT NULL DEFAULT '',
    is_deleted   boolean     NOT NULL DEFAULT false,
    row_version  integer     NOT NULL DEFAULT 0
);

CREATE INDEX ON followup_record(patient_id, visit_date);
CREATE INDEX ON followup_record(dept_code, visit_date);
