-- ============================================================================
-- platform_iot —— 体征监测域（居家/院内设备实时回传）。家庭病床/慢病管理的基础。
-- 见 docs/08-数据库设计.md。高频时序：vital_sign 建议按 measured_at 月分区/TimescaleDB；
-- 此处演示用普通表 + 索引。异常判定用 vital_threshold（生产可个体化）。
-- 只存 patient_id 引用。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform_iot;
SET search_path TO platform_iot;

-- ---- 体征阈值（异常判定规则）----------------------------------------------
CREATE TABLE vital_threshold (
    metric    varchar(16) PRIMARY KEY,           -- bp/glucose/spo2/hr/temp/weight
    low_num   numeric(8,2),
    high_num  numeric(8,2),
    unit      varchar(16),
    label     varchar(64)
);

-- ---- 体征时序 --------------------------------------------------------------
CREATE TABLE vital_sign (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id    varchar(64) NOT NULL,
    metric        varchar(16) NOT NULL,
    value_num     numeric(8,2),                   -- 主数值（如血压取收缩压）
    value_text    varchar(32),                    -- 显示值（如血压 "140/90"）
    unit          varchar(16),
    measured_at   timestamptz NOT NULL,
    source        varchar(8)  NOT NULL DEFAULT 'device',  -- device/nurse/self
    device_id     varchar(64),
    abnormal_flag boolean     NOT NULL DEFAULT false,
    org_id        varchar(32),
    dept_code     varchar(32),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_vital_patient_time ON vital_sign(patient_id, measured_at DESC);
CREATE INDEX ix_vital_abnormal     ON vital_sign(patient_id, abnormal_flag);
