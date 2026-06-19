-- ============================================================================
-- scenario_homebed —— 场景002 家庭病床。建床/准入审核/医嘱任务/出院结算。
-- 复用平台域：患者(platform_patient)、体征(platform_iot)、清分(platform_clearing)、档案(platform_archive)。
-- 只存 patient_id 引用。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS scenario_homebed;
SET search_path TO scenario_homebed;

-- ---- 病床（建床→准入审核→在床→出院）-------------------------------------
CREATE TABLE bed (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bed_no           varchar(32) NOT NULL UNIQUE,
    patient_id       varchar(64) NOT NULL,
    status           varchar(16) NOT NULL DEFAULT 'reviewing',  -- reviewing/admitted/discharged/rejected
    care_level       varchar(16),                -- 一级护理/二级护理/三级护理
    attending_doctor varchar(64),
    admit_date       date,
    discharge_date   date,
    review_note      varchar(128),
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
CREATE INDEX ix_bed_dept    ON bed(dept_code);
CREATE INDEX ix_bed_status  ON bed(status);
CREATE INDEX ix_bed_patient ON bed(patient_id);

-- ---- 护理/医嘱任务（任务调度）---------------------------------------------
CREATE TABLE care_task (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bed_no       varchar(32) NOT NULL REFERENCES bed(bed_no),
    type         varchar(16) NOT NULL,           -- 查房/换药/体征采集/送药
    content      varchar(128),
    status       varchar(8)  NOT NULL DEFAULT 'todo',  -- todo/done
    assignee     varchar(64),
    scheduled_at timestamptz,
    done_at      timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_caretask_bed ON care_task(bed_no);
