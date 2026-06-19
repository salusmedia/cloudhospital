-- ============================================================================
-- scenario_referral —— 转诊一件事（V10 最完整子系统，作为首个端到端样例）
-- 见 docs/08-数据库设计.md 第 7 节。只存 patient_id 引用，不存患者主数据。
-- 业务表带公共字段（org_id/dept_code 驱动数据权限；跨机构可见性靠 platform_identity.record_grant）。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS scenario_referral;
SET search_path TO scenario_referral;

-- ---- 转诊单 -----------------------------------------------------------------
CREATE TABLE referral (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no           varchar(32) NOT NULL UNIQUE,   -- ZZ-2026-06-00123
    patient_id       varchar(64) NOT NULL,          -- 引用 platform_patient
    source_org       varchar(32) NOT NULL,
    source_doctor    varchar(64) NOT NULL,
    target_org       varchar(32),
    target_doctor    varchar(64),
    type             varchar(16) NOT NULL,          -- 上转/下转/平转/急诊/MDT
    risk_level       varchar(16) NOT NULL,          -- 红/黄/绿/急危
    status           varchar(16) NOT NULL DEFAULT 'applying',
    appointment_slot varchar(64),
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
CREATE INDEX ix_ref_patient ON referral(patient_id);
CREATE INDEX ix_ref_source  ON referral(source_org);
CREATE INDEX ix_ref_target  ON referral(target_org);
CREATE INDEX ix_ref_dept    ON referral(dept_code);
CREATE INDEX ix_ref_deleted ON referral(is_deleted);

-- ---- 七节点积分链 -----------------------------------------------------------
CREATE TABLE referral_node (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no    varchar(32) NOT NULL REFERENCES referral(ref_no),
    node      varchar(32) NOT NULL,               -- 首诊评估/资料打包/转诊申请/接收确认/下转方案/接续确认/随访执行
    seq       integer     NOT NULL,
    done_at   timestamptz,
    operator  varchar(64),
    UNIQUE (ref_no, node)
);
CREATE INDEX ix_node_ref ON referral_node(ref_no);

-- ---- 规范转诊五要素 ---------------------------------------------------------
CREATE TABLE referral_check (
    id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no varchar(32) NOT NULL REFERENCES referral(ref_no),
    item   varchar(64) NOT NULL,
    passed boolean     NOT NULL DEFAULT false,
    UNIQUE (ref_no, item)
);

-- ---- 资料互认包 -------------------------------------------------------------
CREATE TABLE referral_package (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no             varchar(32) NOT NULL REFERENCES referral(ref_no),
    doc_type           varchar(32) NOT NULL,       -- 病历摘要/检验/影像/心电/处方
    source_report_id   varchar(64),                -- 引用 platform_archive
    mutual_recognition boolean     NOT NULL DEFAULT false,
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_pkg_ref ON referral_package(ref_no);

-- ---- 个人服务信用账户（不按月清零）-----------------------------------------
CREATE TABLE credit_account (
    user_id    varchar(64) PRIMARY KEY,           -- 引用 platform_identity.app_user
    balance    numeric(12,2) NOT NULL DEFAULT 0,  -- 累计可兑现金额
    points     integer     NOT NULL DEFAULT 0,    -- 累计积分
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 积分流水：每个节点完成即记分，三源（DRG/绩效/结余）折算（append-only）
CREATE TABLE credit_ledger (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     varchar(64) NOT NULL,
    ref_no      varchar(32) NOT NULL REFERENCES referral(ref_no),
    node        varchar(32) NOT NULL,
    points      integer     NOT NULL,
    drg_amt     numeric(12,2) NOT NULL DEFAULT 0,
    perf_amt    numeric(12,2) NOT NULL DEFAULT 0,
    surplus_amt numeric(12,2) NOT NULL DEFAULT 0,
    occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_credit_user ON credit_ledger(user_id);
CREATE INDEX ix_credit_ref  ON credit_ledger(ref_no);

-- ---- 机构协同分账（机构→科室/个人二次分配）--------------------------------
CREATE TABLE org_settlement (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        varchar(32) NOT NULL,
    period        varchar(7)  NOT NULL,           -- YYYY-MM
    service_amount numeric(14,2) NOT NULL DEFAULT 0,
    quality_bonus  numeric(14,2) NOT NULL DEFAULT 0,
    actual_alloc   numeric(14,2) NOT NULL DEFAULT 0,
    UNIQUE (org_id, period)
);
