-- ============================================================================
-- 外部数据源表 —— 生产中由外部系统对接同步，开发期用种子数据填充以支撑完整交互。
--   platform_insurance   医保局：参保、报销规则、异常费用
--   platform_dict        卫健委：检查互认目录等参考字典
--   platform_appointment HIS 挂号：号源
-- 见 docs/08-数据库设计.md。本迁移仅建表；数据由 scripts/seed_external.py 灌入。
-- ============================================================================

-- ---- 医保（医保局对接）------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS platform_insurance;
SET search_path TO platform_insurance;

-- 报销规则：按 转诊类型 × 参保类型 × 是否备案 定起付线/报销比例/封顶
CREATE TABLE insurance_policy_rule (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    referral_type  varchar(16)  NOT NULL,        -- up/down/flat/emergency
    insurance_type varchar(24)  NOT NULL,        -- 城乡居民/职工医保
    filed          boolean      NOT NULL,        -- 是否转诊备案
    deductible     numeric(10,2) NOT NULL,       -- 起付线
    reimburse_ratio numeric(4,3) NOT NULL,       -- 报销比例
    cap_line       numeric(12,2) NOT NULL,       -- 年度封顶
    note           varchar(128),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (referral_type, insurance_type, filed)
);

-- 患者参保信息（医保局）
CREATE TABLE patient_insurance (
    patient_id        varchar(64) PRIMARY KEY,   -- 引用 platform_patient.patient
    insurance_type    varchar(24) NOT NULL,
    pooling_region    varchar(32),               -- 统筹区
    filed             boolean     NOT NULL DEFAULT false,
    annual_reimbursed numeric(12,2) NOT NULL DEFAULT 0,
    cap_line          numeric(12,2) NOT NULL DEFAULT 0,
    updated_at        timestamptz NOT NULL DEFAULT now()
);

-- 异常费用（医保智能审查产出）
CREATE TABLE fee_abnormal_case (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id        varchar(64),
    org_id            varchar(32),
    fee               numeric(12,2) NOT NULL,
    reason            varchar(64) NOT NULL,
    review_conclusion varchar(128),
    status            varchar(16) NOT NULL DEFAULT 'pending',
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- ---- 参考字典（卫健委对接）-------------------------------------------------
CREATE SCHEMA IF NOT EXISTS platform_dict;
SET search_path TO platform_dict;

-- 检查互认目录：项目 × 有效期 × 互认范围
CREATE TABLE mutual_recognition_catalog (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category        varchar(16) NOT NULL,        -- 影像/检验/功能
    item_name       varchar(64) NOT NULL,
    valid_days      integer     NOT NULL,        -- 互认有效期（天）
    recognize_scope varchar(32) NOT NULL,        -- 市级医共体内/全省/全国
    status          varchar(16) NOT NULL DEFAULT 'active',
    UNIQUE (category, item_name)
);

-- ---- 号源（HIS 挂号对接）---------------------------------------------------
CREATE SCHEMA IF NOT EXISTS platform_appointment;
SET search_path TO platform_appointment;

CREATE TABLE appointment_slot (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     varchar(32) NOT NULL,
    dept_code  varchar(32) NOT NULL,
    slot_time  timestamptz NOT NULL,
    slot_type  varchar(24) NOT NULL,             -- 专家转诊号/普通号/急诊绿通
    total      integer     NOT NULL,
    remaining  integer     NOT NULL,
    status     varchar(16) NOT NULL DEFAULT 'open',
    UNIQUE (org_id, dept_code, slot_time, slot_type)
);
CREATE INDEX ix_slot_org_dept ON appointment_slot(org_id, dept_code);
