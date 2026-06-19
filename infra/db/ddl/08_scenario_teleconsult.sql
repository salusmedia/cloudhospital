-- ============================================================================
-- scenario_teleconsult —— 场景006 在线复诊（互联网诊疗闭环）。
-- 复用平台域：患者(platform_patient)、清分(platform_clearing)、档案(platform_archive)。
-- 只存 patient_id 引用；计酬走 platform_clearing.split_income。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS scenario_teleconsult;
SET search_path TO scenario_teleconsult;

-- ---- 复诊会话（候诊→接诊→结束）-------------------------------------------
CREATE TABLE consult (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    consult_no      varchar(32) NOT NULL UNIQUE,
    patient_id      varchar(64) NOT NULL,        -- 引用 platform_patient
    status          varchar(16) NOT NULL DEFAULT 'waiting',  -- waiting/in_progress/finished
    chief_complaint varchar(256),
    ai_triage       varchar(8),                  -- low/medium/high（AI预问诊风险分级）
    accepted_by     varchar(64),
    accepted_at     timestamptz,
    finished_at     timestamptz,
    -- 公共字段
    org_id      varchar(32) NOT NULL,
    dept_code   varchar(32) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    created_by  varchar(64) NOT NULL DEFAULT '',
    updated_by  varchar(64) NOT NULL DEFAULT '',
    is_deleted  boolean     NOT NULL DEFAULT false,
    row_version integer     NOT NULL DEFAULT 0
);
CREATE INDEX ix_consult_dept    ON consult(dept_code);
CREATE INDEX ix_consult_status  ON consult(status);
CREATE INDEX ix_consult_patient ON consult(patient_id);

-- ---- 电子处方（含 AI 审方结果）-------------------------------------------
CREATE TABLE consult_rx (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    consult_no varchar(32) NOT NULL REFERENCES consult(consult_no),
    drug_name  varchar(128) NOT NULL,
    usage      varchar(64),
    ai_review  varchar(16) NOT NULL DEFAULT 'passed',  -- passed/warn
    review_note varchar(128),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_consultrx_no ON consult_rx(consult_no);
