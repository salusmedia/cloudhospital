-- ============================================================================
-- platform_archive —— 健康档案（跨院汇聚的就诊/诊断/检验影像/处方）。
-- 见 docs/08-数据库设计.md 第 6 节。生产由各院 HIS/LIS/PACS 汇聚同步。
-- 临床内容（诊断/结论）属敏感数据：库内是访问受控真源，禁止写日志/进提交记录/喂 AI。
-- 只存 patient_id 引用（患者主数据在 platform_patient）。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform_archive;
SET search_path TO platform_archive;

-- ---- 就诊记录 --------------------------------------------------------------
CREATE TABLE encounter (
    encounter_id    varchar(64) PRIMARY KEY,
    patient_id      varchar(64) NOT NULL,
    org_id          varchar(32) NOT NULL,
    dept_code       varchar(32) NOT NULL,
    type            varchar(16) NOT NULL,        -- 门诊/住院/急诊
    visit_time      timestamptz NOT NULL,
    doctor_id       varchar(64),
    chief_complaint varchar(256),                -- 主诉
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_enc_patient ON encounter(patient_id);
CREATE INDEX ix_enc_org     ON encounter(org_id);

-- ---- 诊断 ------------------------------------------------------------------
CREATE TABLE diagnosis (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id   varchar(64) NOT NULL,
    encounter_id varchar(64) REFERENCES encounter(encounter_id),
    icd_code     varchar(16),
    name         varchar(128) NOT NULL,
    is_chronic   boolean NOT NULL DEFAULT false,
    diagnosed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_dx_patient ON diagnosis(patient_id);

-- ---- 检验/影像/功能报告 ----------------------------------------------------
CREATE TABLE report (
    report_id    varchar(64) PRIMARY KEY,
    patient_id   varchar(64) NOT NULL,
    encounter_id varchar(64) REFERENCES encounter(encounter_id),
    category     varchar(16) NOT NULL,           -- 检验/影像/功能
    item_name    varchar(64) NOT NULL,           -- 与互认目录 item_name 对应
    conclusion   varchar(512),
    report_time  timestamptz NOT NULL,
    org_id       varchar(32),
    file_id      varchar(64),                    -- 引用 platform_file（原件）
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_rep_patient ON report(patient_id);

-- ---- 处方 ------------------------------------------------------------------
CREATE TABLE prescription (
    rx_id        varchar(64) PRIMARY KEY,
    patient_id   varchar(64) NOT NULL,
    encounter_id varchar(64) REFERENCES encounter(encounter_id),
    status       varchar(16) NOT NULL DEFAULT 'issued',  -- issued/dispensed
    doctor_id    varchar(64),
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_rx_patient ON prescription(patient_id);

CREATE TABLE prescription_item (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rx_id     varchar(64) NOT NULL REFERENCES prescription(rx_id),
    drug_code varchar(32),
    drug_name varchar(128) NOT NULL,
    usage     varchar(64),
    course    varchar(64)
);
CREATE INDEX ix_rxitem_rx ON prescription_item(rx_id);
