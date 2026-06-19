-- ============================================================================
-- platform_clearing —— 阳光收入·空中清分：差异化计价 + 多方分账 + 个人账户
-- 见 docs/08-数据库设计.md 第 5 节。与 py_common.clearing.split_income 对应。
-- 台账（income_split / settlement_ledger）只追加，纠错走红冲。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform_clearing;
SET search_path TO platform_clearing;

-- ---- 计价规则：按 场景×服务×机构tier×职称 分档 ------------------------------
CREATE TABLE service_rate_card (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_code      varchar(32)  NOT NULL,
    service_type       varchar(64)  NOT NULL,    -- 报告解读/图文咨询/视频复诊/MDT会诊/转诊节点/随访/服务包
    applies_org_tier   varchar(16)  NOT NULL DEFAULT 'any',  -- 三级/二级/一级/any
    applies_title_rank integer      NOT NULL DEFAULT 0,      -- 职称门槛（>= 生效）
    unit_price         numeric(12,2) NOT NULL,
    individual_ratio   numeric(5,4) NOT NULL,    -- 四者之和应为 1
    dept_ratio         numeric(5,4) NOT NULL DEFAULT 0,
    org_ratio          numeric(5,4) NOT NULL DEFAULT 0,
    platform_ratio     numeric(5,4) NOT NULL DEFAULT 0,
    floor_price        numeric(12,2),            -- 个人到账保底（转诊积分单价保底 1.5）
    cap_price          numeric(12,2),            -- 个人到账封顶（封顶 3.5）
    effective_from     date         NOT NULL DEFAULT CURRENT_DATE,
    effective_to       date,
    status             varchar(16)  NOT NULL DEFAULT 'active',
    created_at         timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_rate_lookup
    ON service_rate_card(scenario_code, service_type, applies_org_tier, status);

-- ---- 计酬事件：一次可计酬服务 -----------------------------------------------
CREATE TABLE income_event (
    event_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_code     varchar(32)  NOT NULL,
    service_type      varchar(64)  NOT NULL,
    performer_user_id varchar(64)  NOT NULL,     -- 引用 platform_identity.app_user
    perform_org_id    varchar(32)  NOT NULL,     -- 当次执业机构（收入回流依据）
    engagement_mode   varchar(16)  NOT NULL,     -- in_hospital 院内 / multi_site 院外
    patient_id        varchar(64),               -- 引用 platform_patient
    ref_order_id      varchar(64),
    gross_amount      numeric(12,2) NOT NULL,
    occurred_at       timestamptz  NOT NULL DEFAULT now(),
    clearing_status   varchar(16)  NOT NULL DEFAULT 'pending'  -- pending/cleared/reversed
);
CREATE INDEX ix_income_performer ON income_event(performer_user_id);
CREATE INDEX ix_income_org       ON income_event(perform_org_id);
CREATE INDEX ix_income_status    ON income_event(clearing_status);

-- ---- 多方分账明细（append-only）---------------------------------------------
CREATE TABLE income_split (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id   uuid    NOT NULL REFERENCES income_event(event_id),
    payee_type varchar(16) NOT NULL,             -- individual/dept/org/platform
    payee_id   varchar(64) NOT NULL,
    ratio      numeric(5,4),
    amount     numeric(12,2) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_split_event ON income_split(event_id);
CREATE INDEX ix_split_payee ON income_split(payee_type, payee_id);

-- ---- 个人绩效系数（量×质×响应×评价）----------------------------------------
CREATE TABLE staff_perf_coefficient (
    user_id       varchar(64) NOT NULL,
    period        varchar(7)  NOT NULL,           -- YYYY-MM
    volume_coef   numeric(4,3) NOT NULL DEFAULT 1,
    quality_coef  numeric(4,3) NOT NULL DEFAULT 1,
    response_coef numeric(4,3) NOT NULL DEFAULT 1,
    rating_coef   numeric(4,3) NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, period)
);

-- ---- 清分账户与流水（append-only）-------------------------------------------
CREATE TABLE settlement_account (
    account_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type varchar(16) NOT NULL,              -- org/dept/individual
    owner_id   varchar(64) NOT NULL,
    balance    numeric(14,2) NOT NULL DEFAULT 0,
    UNIQUE (owner_type, owner_id)
);

CREATE TABLE settlement_ledger (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  uuid    NOT NULL REFERENCES settlement_account(account_id),
    event_id    uuid REFERENCES income_event(event_id),
    amount      numeric(12,2) NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    clearing_ref varchar(64)                       -- 持牌机构空中清分号
);
CREATE INDEX ix_ledger_account ON settlement_ledger(account_id);
