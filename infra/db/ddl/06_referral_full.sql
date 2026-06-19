-- ============================================================================
-- 转诊一件事 · 完整功能补充表（scenario_referral）。对齐 V10 患者/医生/管理/激励四视图。
-- 已有：referral / referral_node / referral_check / referral_package /
--       credit_account / credit_ledger / org_settlement（见 03_scenario_referral.sql）
-- 本文件新增：知情同意 / 时间轴 / 下转康复方案 / MDT会诊 / 异常预警。
-- ============================================================================

SET search_path TO scenario_referral;

-- ---- 知情同意 · 电子签署记录 -----------------------------------------------
CREATE TABLE referral_consent (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no     varchar(32) NOT NULL REFERENCES referral(ref_no),
    doc_name   varchar(64) NOT NULL,            -- 转诊路径确认书/费用及报销告知书/...
    seq        integer     NOT NULL DEFAULT 0,
    signed     boolean     NOT NULL DEFAULT false,
    signed_at  timestamptz,
    signer     varchar(64),
    UNIQUE (ref_no, doc_name)
);
CREATE INDEX ix_consent_ref ON referral_consent(ref_no);

-- ---- 转诊时间轴（进度跟踪）-------------------------------------------------
CREATE TABLE referral_track (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no      varchar(32) NOT NULL REFERENCES referral(ref_no),
    seq         integer     NOT NULL,
    title       varchar(64) NOT NULL,
    detail      varchar(256),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    operator    varchar(64)
);
CREATE INDEX ix_track_ref ON referral_track(ref_no);

-- ---- 下转康复方案 ----------------------------------------------------------
CREATE TABLE downward_plan (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no      varchar(32) NOT NULL REFERENCES referral(ref_no),
    summary     varchar(512),
    review_plan varchar(512),                   -- 复查节点
    status      varchar(16) NOT NULL DEFAULT 'issued',  -- issued/accepted
    created_by  varchar(64),
    created_at  timestamptz NOT NULL DEFAULT now(),
    accepted_at timestamptz,
    UNIQUE (ref_no)
);
CREATE TABLE downward_plan_drug (
    id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id uuid NOT NULL REFERENCES downward_plan(id),
    drug    varchar(128) NOT NULL,
    usage   varchar(64),
    course  varchar(64)
);
CREATE INDEX ix_plandrug_plan ON downward_plan_drug(plan_id);

-- ---- MDT 多学科会诊 --------------------------------------------------------
CREATE TABLE mdt_session (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no       varchar(32) REFERENCES referral(ref_no),
    topic        varchar(128) NOT NULL,
    case_summary varchar(512),
    scheduled_at timestamptz,
    status       varchar(16) NOT NULL DEFAULT 'scheduled',  -- scheduled/done
    host_user    varchar(64),
    org_id       varchar(32),
    dept_code    varchar(32),
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mdt_expert (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mdt_id    uuid NOT NULL REFERENCES mdt_session(id),
    user_id   varchar(64),
    name      varchar(64) NOT NULL,
    dept      varchar(64),
    org       varchar(64),
    role      varchar(32),                       -- 主持/参与
    confirmed boolean NOT NULL DEFAULT false
);
CREATE TABLE mdt_opinion (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mdt_id    uuid NOT NULL REFERENCES mdt_session(id),
    user_id   varchar(64),
    name      varchar(64),
    opinion   varchar(1024) NOT NULL,
    signed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_mdtexpert_mdt ON mdt_expert(mdt_id);
CREATE INDEX ix_mdtopinion_mdt ON mdt_opinion(mdt_id);

-- ---- 异常转诊预警（管理端处置）--------------------------------------------
CREATE TABLE referral_alert (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref_no     varchar(32) REFERENCES referral(ref_no),
    level      varchar(8)  NOT NULL,             -- p1/p2/p3
    category   varchar(32) NOT NULL,             -- 超时/费用异常/重复检查/指征不符
    title      varchar(128) NOT NULL,
    detail     varchar(256),
    status     varchar(16) NOT NULL DEFAULT 'open',  -- open/handled
    handled_by varchar(64),
    handled_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_alert_status ON referral_alert(status);
