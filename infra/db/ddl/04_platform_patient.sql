-- ============================================================================
-- platform_patient —— 患者主数据（唯一真源）。敏感字段 pgcrypto 加密落盘。
-- 见 docs/08-数据库设计.md 第 6 节。场景库只存 patient_id 引用，不复制这里的数据。
-- 加密密钥运行时注入（pgp_sym_encrypt/decrypt 的 key 由应用传入），绝不写死/不进库。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform_patient;
SET search_path TO platform_patient;

CREATE TABLE patient (
    patient_id   varchar(64)  PRIMARY KEY,
    mrn          varchar(32),                 -- 病历号
    name_enc     bytea        NOT NULL,        -- 姓名（pgp_sym_encrypt 加密）
    id_card_enc  bytea,                        -- 身份证（加密）
    id_card_hash varchar(64),                  -- 身份证 sha256（不可逆，查重/匹配用）
    phone_enc    bytea,                        -- 手机号（加密）
    gender       varchar(8),
    birth_date   date,
    org_id       varchar(32)  NOT NULL,
    health_score integer,
    risk_level   varchar(16),
    created_at   timestamptz  NOT NULL DEFAULT now(),
    updated_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_patient_org    ON patient(org_id);
CREATE INDEX ix_patient_idhash ON patient(id_card_hash);
