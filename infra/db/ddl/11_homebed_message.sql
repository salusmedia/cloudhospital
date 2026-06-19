-- ============================================================================
-- scenario_homebed 补充：远程问诊消息（医护↔患者/家属 图文）。
-- 运营看板/质控为聚合指标，无需新表（从 bed/care_task/platform_iot 计算）。
-- ============================================================================

SET search_path TO scenario_homebed;

CREATE TABLE bed_message (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bed_no      varchar(32) NOT NULL REFERENCES bed(bed_no),
    sender      varchar(64) NOT NULL,
    sender_role varchar(16) NOT NULL,            -- doctor/nurse/patient/family
    content     varchar(512) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_bedmsg_bed ON bed_message(bed_no, created_at);
