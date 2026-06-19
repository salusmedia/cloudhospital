-- ============================================================================
-- platform_consent —— 数据授权/知情同意（全程留痕·可撤回）。V10「数据授权管理」。
-- platform_file    —— 文件对象元数据（报告PDF/影像/签署件）。原件走对象存储(MinIO)。
-- 只存 patient_id 引用。
-- ============================================================================

-- ---- 数据授权 -------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS platform_consent;
SET search_path TO platform_consent;

CREATE TABLE consent_record (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id    varchar(64) NOT NULL,
    grantee       varchar(32) NOT NULL,          -- ai_assistant/insurer/research/org
    grantee_name  varchar(64),
    purpose       varchar(128) NOT NULL,
    scope         varchar(128),
    status        varchar(16) NOT NULL DEFAULT 'granted',  -- granted/revoked
    granted_at    timestamptz NOT NULL DEFAULT now(),
    revoked_at    timestamptz,
    evidence_hash varchar(64),                   -- 留痕（操作快照哈希）
    updated_by    varchar(64)
);
CREATE INDEX ix_consent_patient ON consent_record(patient_id);

-- ---- 文件元数据 -----------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS platform_file;
SET search_path TO platform_file;

CREATE TABLE file_object (
    file_id       varchar(64) PRIMARY KEY,
    filename      varchar(256) NOT NULL,
    mime          varchar(64),
    size_bytes    bigint,
    sha256        varchar(64),
    storage_uri   varchar(256),                  -- 对象存储 key（演示占位）
    owner_user_id varchar(64),
    patient_id    varchar(64),
    dept_code     varchar(32),
    scenario      varchar(32),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_file_patient ON file_object(patient_id);
