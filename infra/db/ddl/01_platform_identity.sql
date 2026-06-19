-- ============================================================================
-- platform_identity —— 机构/科室/用户/RBAC/数据权限/跨机构授权/场景授权/医护身份
-- 见 docs/08-数据库设计.md 第 4、5 节。PostgreSQL 14+。
-- 公共字段约定（业务表）：id/org_id/dept_code/created_at/updated_at/created_by/
--                         updated_by/is_deleted/row_version（见 py_common.models.CommonColumns）。
-- 配置/维度表按需精简，不强制全套公共字段。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform_identity;
SET search_path TO platform_identity;

-- ---- 机构与科室（医共体多级）------------------------------------------------
CREATE TABLE organization (
    org_id      varchar(32)  PRIMARY KEY,
    name        varchar(128) NOT NULL,
    tier        varchar(16)  NOT NULL,          -- 三级 / 二级 / 一级 / 社区
    group_id    varchar(32),                    -- 所属医共体
    parent_id   varchar(32) REFERENCES organization(org_id),
    status      varchar(16)  NOT NULL DEFAULT 'active',
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_org_group  ON organization(group_id);
CREATE INDEX ix_org_parent ON organization(parent_id);

CREATE TABLE department (
    dept_code   varchar(32)  PRIMARY KEY,        -- ASCII 科室代码（驱动数据权限）
    name        varchar(128) NOT NULL,
    org_id      varchar(32)  NOT NULL REFERENCES organization(org_id),
    parent_code varchar(32) REFERENCES department(dept_code),
    type        varchar(32),
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_dept_org ON department(org_id);

-- ---- 用户与 RBAC ------------------------------------------------------------
CREATE TABLE app_user (
    user_id           varchar(64)  PRIMARY KEY,
    username          varchar(64)  NOT NULL UNIQUE,
    name              varchar(128) NOT NULL,
    password_hash     varchar(256),              -- 对接 HIS/LDAP 时可空
    source            varchar(16)  NOT NULL DEFAULT 'local',   -- his/ldap/local
    user_type         varchar(16)  NOT NULL,     -- resident/staff/regulator/admin
    org_id            varchar(32) REFERENCES organization(org_id),
    primary_dept_code varchar(32) REFERENCES department(dept_code),
    status            varchar(16)  NOT NULL DEFAULT 'active',
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_user_org  ON app_user(org_id);
CREATE INDEX ix_user_type ON app_user(user_type);

CREATE TABLE role (
    role_code   varchar(32)  PRIMARY KEY,        -- ASCII，如 doctor/nurse/regulator
    name        varchar(64)  NOT NULL,
    builtin     boolean      NOT NULL DEFAULT false,
    description varchar(256)
);

CREATE TABLE permission (
    perm_code   varchar(64)  PRIMARY KEY,
    name        varchar(128) NOT NULL,
    type        varchar(16)  NOT NULL,           -- menu/action/api
    resource    varchar(128)
);

CREATE TABLE user_role (
    user_id   varchar(64) NOT NULL REFERENCES app_user(user_id),
    role_code varchar(32) NOT NULL REFERENCES role(role_code),
    PRIMARY KEY (user_id, role_code)
);

CREATE TABLE role_permission (
    role_code varchar(32) NOT NULL REFERENCES role(role_code),
    perm_code varchar(64) NOT NULL REFERENCES permission(perm_code),
    PRIMARY KEY (role_code, perm_code)
);

-- ---- 数据权限：科室 scope + 家庭成员 + 跨机构授权 ----------------------------
CREATE TABLE user_data_scope (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    varchar(64) NOT NULL REFERENCES app_user(user_id),
    scope_type varchar(16) NOT NULL,             -- all/org/dept/dept_and_sub/self/custom
    org_id     varchar(32),
    dept_code  varchar(32),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_scope_user ON user_data_scope(user_id);

CREATE TABLE patient_guardian (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       varchar(64) NOT NULL,       -- 引用 platform_patient
    guardian_user_id varchar(64) NOT NULL REFERENCES app_user(user_id),
    relation         varchar(32) NOT NULL,       -- 本人/子女/配偶/父母
    authorized_scope varchar(64),
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_guardian_user    ON patient_guardian(guardian_user_id);
CREATE INDEX ix_guardian_patient ON patient_guardian(patient_id);

-- 跨机构可见性：转诊/MDT/会诊把某条记录授予给目标机构/科室可见
CREATE TABLE record_grant (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type varchar(32) NOT NULL,          -- referral/encounter/report...
    resource_id   varchar(64) NOT NULL,
    grantee_org   varchar(32),
    grantee_dept  varchar(32),
    grant_reason  varchar(32) NOT NULL,          -- referral/mdt/consult
    expire_at     timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_grant_resource ON record_grant(resource_type, resource_id);
CREATE INDEX ix_grant_grantee  ON record_grant(grantee_org, grantee_dept);

-- ---- 场景注册与场景级授权 ---------------------------------------------------
CREATE TABLE scenario_registry (
    scenario_code varchar(32) PRIMARY KEY,        -- 与场景登记表一致
    name          varchar(128) NOT NULL,
    owner_dept    varchar(32),
    status        varchar(16) NOT NULL DEFAULT 'planning',  -- planning/dev/online/retired
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE scenario_capability (
    scenario_code varchar(32) NOT NULL REFERENCES scenario_registry(scenario_code),
    cap_code      varchar(64) NOT NULL,           -- 如 prescribe/sign_report/referral.receive
    name          varchar(128) NOT NULL,
    PRIMARY KEY (scenario_code, cap_code)
);

CREATE TABLE staff_scenario_enrollment (
    enrollment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       varchar(64) NOT NULL REFERENCES app_user(user_id),
    scenario_code varchar(32) NOT NULL REFERENCES scenario_registry(scenario_code),
    scenario_role varchar(32) NOT NULL,           -- 接诊医师/发起家庭医生/PI...
    status        varchar(16) NOT NULL DEFAULT 'active',
    enrolled_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, scenario_code)
);
CREATE INDEX ix_enroll_user     ON staff_scenario_enrollment(user_id);
CREATE INDEX ix_enroll_scenario ON staff_scenario_enrollment(scenario_code);

CREATE TABLE enrollment_capability (
    enrollment_id uuid    NOT NULL REFERENCES staff_scenario_enrollment(enrollment_id),
    cap_code      varchar(64) NOT NULL,
    granted       boolean NOT NULL DEFAULT true,
    PRIMARY KEY (enrollment_id, cap_code)
);

-- ---- 医护跨机构身份与资质 ---------------------------------------------------
CREATE TABLE staff_profile (
    user_id           varchar(64) PRIMARY KEY REFERENCES app_user(user_id),
    name              varchar(128) NOT NULL,
    home_org_id       varchar(32) NOT NULL REFERENCES organization(org_id),
    primary_dept_code varchar(32) REFERENCES department(dept_code),
    title             varchar(32),                -- 主任/副主任/主治/住院医/护师/护理员
    title_rank        integer     NOT NULL DEFAULT 0,   -- 计价分档与资质门槛比较
    practice_score    numeric(3,2),               -- 执业评分
    accept_external   boolean     NOT NULL DEFAULT true, -- 院外接单开关
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

-- 一个医护可在多机构执业（主执业 + 多点执业备案）→ 多对多
CREATE TABLE staff_affiliation (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    varchar(64) NOT NULL REFERENCES staff_profile(user_id),
    org_id     varchar(32) NOT NULL REFERENCES organization(org_id),
    affil_type varchar(16) NOT NULL,              -- 主执业 / 多点执业备案
    dept_code  varchar(32),
    status     varchar(16) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, org_id, affil_type)
);
CREATE INDEX ix_affil_user ON staff_affiliation(user_id);
CREATE INDEX ix_affil_org  ON staff_affiliation(org_id);

CREATE TABLE staff_credential (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     varchar(64) NOT NULL REFERENCES staff_profile(user_id),
    type        varchar(32) NOT NULL,             -- 执业医师证/护士执业证/多点执业备案/电子签名CA
    cert_no     varchar(64),
    scope       varchar(128),                     -- 覆盖科室/执业范围
    valid_until date,
    status      varchar(16) NOT NULL DEFAULT 'active',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_cred_user ON staff_credential(user_id);
