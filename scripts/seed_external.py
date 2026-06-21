"""灌入「外部数据源」模拟数据，支撑转诊一件事的完整交互。

生产中这些数据来自外部系统对接（仅作占位说明）：
  - 机构/科室          ← 卫健委机构目录 / HIS
  - 医护身份与资质      ← HR / 卫健委执业注册 / LDAP
  - 患者主数据          ← HIS（敏感字段加密落盘）
  - 参保与报销规则      ← 医保局
  - 检查互认目录        ← 卫健委
  - 号源                ← HIS 挂号
开发期用本脚本灌入，可重复执行（幂等）。

运行：
  cd D:\\claude-coding\\ai-cloud-hospital
  uv run python scripts/seed_external.py
"""

from __future__ import annotations

import hashlib
import os

import psycopg

CONNINFO = os.getenv("SEED_DB", "postgresql://dev:dev@localhost:5432/hospital")
# 与 platform-patient 服务一致的加密密钥（生产由环境注入）
PII_KEY = os.getenv("PLATFORM_PATIENT_PII_KEY", "dev-only-pii-key-change-me")

# ---- 机构（卫健委/HIS）------------------------------------------------------
ORGS = [
    ("wzcvh", "温州市中心医院", "三级", "wz", None),
    ("wmu1", "温医大附属第一医院", "三级", "wz", None),
    ("wtsc", "梧田社区卫生服务中心", "社区", "wz", "wzcvh"),
    ("nhsc", "南汇社区卫生服务中心", "社区", "wz", "wzcvh"),
]
DEPTS = [
    ("card", "心血管内科", "wzcvh", None, "临床"),
    ("endo", "内分泌科", "wzcvh", None, "临床"),
    ("gp_wt", "全科", "wtsc", None, "全科"),
    ("gp_nh", "全科", "nhsc", None, "全科"),
]
# ---- 医护（HR/执业注册）-----------------------------------------------------
USERS = [
    ("u1", "doctor_card", "李医生", "local", "staff", "wzcvh", "card"),
    ("uwmy", "wmingyuan", "王明远", "his", "staff", "wzcvh", "card"),
    ("uliming", "liming", "李明", "his", "staff", "wtsc", "gp_wt"),
    ("u0", "admin", "管理员", "local", "admin", "wzcvh", None),
]
STAFF = [
    # user_id, name, home_org, dept, title, rank, score, accept_external
    ("u1", "李医生", "wzcvh", "card", "主治医师", 2, 4.90, True),
    ("uwmy", "王明远", "wzcvh", "card", "主任医师", 4, 4.97, True),
    ("uliming", "李明", "wtsc", "gp_wt", "家庭医生", 2, 4.85, True),
]
AFFIL = [
    ("u1", "wzcvh", "主执业", "card"),
    ("uwmy", "wzcvh", "主执业", "card"),
    ("uwmy", "wmu1", "多点执业备案", "card"),
    ("uliming", "wtsc", "主执业", "gp_wt"),
]
CREDS = [
    ("u1", "执业医师证", "1103302xxxx0001", "心血管内科", "2031-01-31"),
    ("uwmy", "执业医师证", "1103302xxxx0002", "心血管内科", "2030-12-31"),
    ("uwmy", "多点执业备案", "DD-2026-018", "互联网医院执业", "2027-12-31"),
    ("uwmy", "电子签名CA", "CA-7788", "全院", "2027-03-31"),
    ("uliming", "执业医师证", "1103302xxxx0003", "全科医学", "2029-06-30"),
]
# ---- 患者主数据（HIS，敏感字段加密）----------------------------------------
PATIENTS = [
    # patient_id, mrn, name, id_card, phone, gender, birth, org, score, risk
    ("P-1001", "MRN0001", "张建国", "330302196801011234", "13900139001", "M", "1968-01-01", "wzcvh", 78, "中"),
    ("P-1002", "MRN0002", "陈丽", "330302197905052345", "13900139002", "F", "1979-05-05", "wzcvh", 82, "中"),
    ("P-1003", "MRN0003", "孙晓华", "330302196203033456", "13900139003", "F", "1962-03-03", "wzcvh", 70, "高"),
]
# ---- 参保（医保局）---------------------------------------------------------
PATIENT_INS = [
    ("P-1001", "城乡居民", "温州", True, 12800, 150000),
    ("P-1002", "职工医保", "温州", True, 8600, 300000),
    ("P-1003", "城乡居民", "温州", False, 2000, 150000),
]
INS_RULES = [
    # referral_type, insurance_type, filed, deductible, ratio, cap, note
    ("up", "城乡居民", True, 800, 0.85, 150000, "上转·有备案"),
    ("up", "城乡居民", False, 800, 0.55, 150000, "上转·无备案"),
    ("up", "职工医保", True, 500, 0.90, 300000, "上转·有备案"),
    ("emergency", "城乡居民", True, 500, 0.90, 150000, "急诊绿色通道"),
]
# ---- 检查互认目录（卫健委）-------------------------------------------------
MR_CATALOG = [
    ("影像", "胸部CT平扫", 90, "市级医共体内"),
    ("影像", "心脏彩超", 30, "市级医共体内"),
    ("检验", "血常规", 7, "全省"),
    ("检验", "心肌酶谱", 1, "全省"),
    ("功能", "24h动态心电图", 30, "市级医共体内"),
]
# ---- 号源（HIS 挂号）-------------------------------------------------------
SLOTS = [
    ("wzcvh", "card", "2026-06-19 14:30+08", "专家转诊号", 5, 5),
    ("wzcvh", "card", "2026-06-20 09:00+08", "普通号", 20, 12),
]
# ---- 转诊单（业务，引用上面的患者/机构/医生）-------------------------------
REFERRALS = [
    ("EXT-001", "P-1001", "wtsc", "uliming", "wzcvh", "uwmy", "up", "yellow", "card"),
    ("EXT-002", "P-1002", "nhsc", "uliming", "wzcvh", "uwmy", "up", "red", "card"),
]


def main() -> None:
    with psycopg.connect(CONNINFO) as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO platform_identity.organization(org_id,name,tier,group_id,parent_id)
               VALUES(%s,%s,%s,%s,%s)
               ON CONFLICT(org_id) DO UPDATE SET name=EXCLUDED.name,tier=EXCLUDED.tier""",
            ORGS,
        )
        cur.executemany(
            """INSERT INTO platform_identity.department(dept_code,name,org_id,parent_code,type)
               VALUES(%s,%s,%s,%s,%s)
               ON CONFLICT(dept_code) DO UPDATE SET name=EXCLUDED.name,org_id=EXCLUDED.org_id""",
            DEPTS,
        )
        cur.executemany(
            """INSERT INTO platform_identity.app_user(user_id,username,name,source,user_type,org_id,primary_dept_code,status)
               VALUES(%s,%s,%s,%s,%s,%s,%s,'active')
               ON CONFLICT(user_id) DO UPDATE SET name=EXCLUDED.name,org_id=EXCLUDED.org_id,primary_dept_code=EXCLUDED.primary_dept_code""",
            USERS,
        )
        cur.executemany(
            """INSERT INTO platform_identity.staff_profile(user_id,name,home_org_id,primary_dept_code,title,title_rank,practice_score,accept_external)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT(user_id) DO UPDATE SET title=EXCLUDED.title,title_rank=EXCLUDED.title_rank,practice_score=EXCLUDED.practice_score""",
            STAFF,
        )
        cur.execute("DELETE FROM platform_identity.staff_affiliation")
        cur.executemany(
            """INSERT INTO platform_identity.staff_affiliation(user_id,org_id,affil_type,dept_code,status)
               VALUES(%s,%s,%s,%s,'active')""",
            AFFIL,
        )
        cur.execute("DELETE FROM platform_identity.staff_credential")
        cur.executemany(
            """INSERT INTO platform_identity.staff_credential(user_id,type,cert_no,scope,valid_until,status)
               VALUES(%s,%s,%s,%s,%s,'active')""",
            CREDS,
        )

        # 患者（加密落盘）
        for pid, mrn, name, idc, phone, gender, birth, org, score, risk in PATIENTS:
            idh = hashlib.sha256(idc.encode()).hexdigest()
            cur.execute(
                """INSERT INTO platform_patient.patient
                     (patient_id,mrn,name_enc,id_card_enc,id_card_hash,phone_enc,gender,birth_date,org_id,health_score,risk_level)
                   VALUES(%s,%s,pgp_sym_encrypt(%s::text,%s::text),pgp_sym_encrypt(%s::text,%s::text),%s,
                          pgp_sym_encrypt(%s::text,%s::text),%s,%s,%s,%s,%s)
                   ON CONFLICT(patient_id) DO UPDATE SET
                     name_enc=EXCLUDED.name_enc,id_card_enc=EXCLUDED.id_card_enc,id_card_hash=EXCLUDED.id_card_hash,
                     phone_enc=EXCLUDED.phone_enc,gender=EXCLUDED.gender,org_id=EXCLUDED.org_id,
                     health_score=EXCLUDED.health_score,risk_level=EXCLUDED.risk_level""",
                (pid, mrn, name, PII_KEY, idc, PII_KEY, idh, phone, PII_KEY, gender, birth, org, score, risk),
            )

        cur.executemany(
            """INSERT INTO platform_insurance.patient_insurance(patient_id,insurance_type,pooling_region,filed,annual_reimbursed,cap_line)
               VALUES(%s,%s,%s,%s,%s,%s)
               ON CONFLICT(patient_id) DO UPDATE SET insurance_type=EXCLUDED.insurance_type,filed=EXCLUDED.filed,
                 annual_reimbursed=EXCLUDED.annual_reimbursed,cap_line=EXCLUDED.cap_line""",
            PATIENT_INS,
        )
        cur.executemany(
            """INSERT INTO platform_insurance.insurance_policy_rule(referral_type,insurance_type,filed,deductible,reimburse_ratio,cap_line,note)
               VALUES(%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT(referral_type,insurance_type,filed) DO UPDATE SET
                 deductible=EXCLUDED.deductible,reimburse_ratio=EXCLUDED.reimburse_ratio,cap_line=EXCLUDED.cap_line""",
            INS_RULES,
        )
        cur.executemany(
            """INSERT INTO platform_dict.mutual_recognition_catalog(category,item_name,valid_days,recognize_scope)
               VALUES(%s,%s,%s,%s)
               ON CONFLICT(category,item_name) DO UPDATE SET valid_days=EXCLUDED.valid_days,recognize_scope=EXCLUDED.recognize_scope""",
            MR_CATALOG,
        )
        cur.executemany(
            """INSERT INTO platform_appointment.appointment_slot(org_id,dept_code,slot_time,slot_type,total,remaining)
               VALUES(%s,%s,%s,%s,%s,%s)
               ON CONFLICT(org_id,dept_code,slot_time,slot_type) DO UPDATE SET remaining=EXCLUDED.remaining""",
            SLOTS,
        )

        # 计价规则（若无）
        cur.execute(
            """INSERT INTO platform_clearing.service_rate_card
                 (scenario_code,service_type,applies_org_tier,applies_title_rank,unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio,status)
               SELECT 'scenario-019','referral_receive','any',0,50.00,0.60,0.20,0.20,0.00,'active'
               WHERE NOT EXISTS(SELECT 1 FROM platform_clearing.service_rate_card WHERE service_type='referral_receive')"""
        )

        # 转诊单（先清本脚本的 EXT-*，按 FK 安全顺序清全部子表，保证可重复执行）
        cur.execute("DELETE FROM scenario_referral.mdt_opinion WHERE mdt_id IN (SELECT id FROM scenario_referral.mdt_session WHERE ref_no LIKE 'EXT-%')")
        cur.execute("DELETE FROM scenario_referral.mdt_expert WHERE mdt_id IN (SELECT id FROM scenario_referral.mdt_session WHERE ref_no LIKE 'EXT-%')")
        cur.execute("DELETE FROM scenario_referral.mdt_session WHERE ref_no LIKE 'EXT-%'")
        cur.execute("DELETE FROM scenario_referral.downward_plan_drug WHERE plan_id IN (SELECT id FROM scenario_referral.downward_plan WHERE ref_no LIKE 'EXT-%')")
        cur.execute("DELETE FROM scenario_referral.downward_plan WHERE ref_no LIKE 'EXT-%'")
        for _t in ("referral_node", "credit_ledger", "referral_consent", "referral_check", "referral_package", "referral_track"):
            cur.execute(f"DELETE FROM scenario_referral.{_t} WHERE ref_no LIKE 'EXT-%'")
        cur.execute("DELETE FROM scenario_referral.referral WHERE ref_no LIKE 'EXT-%'")
        cur.executemany(
            """INSERT INTO scenario_referral.referral
                 (ref_no,patient_id,source_org,source_doctor,target_org,target_doctor,type,risk_level,status,org_id,dept_code,created_by)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'applying','wzcvh',%s,'seed')""",
            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]) for r in REFERRALS],
        )

        # ---- 转诊单子数据：五要素/资料/同意/时间轴 ----
        ext_refs = [r[0] for r in REFERRALS]
        for t in ("referral_check", "referral_package", "referral_consent", "referral_track"):
            cur.execute(f"DELETE FROM scenario_referral.{t} WHERE ref_no LIKE 'EXT-%'")
        for ref in ext_refs:
            for item in ["首诊摘要≥50字", "完整度≥85%", "转诊理由明确", "接收时限达标", "随访计划完整"]:
                cur.execute("INSERT INTO scenario_referral.referral_check(ref_no,item,passed) VALUES(%s,%s,true)", (ref, item))
            for doc, mr in [("病历摘要", False), ("血常规", True), ("胸部CT平扫", True), ("心脏彩超", True), ("处方记录", False)]:
                cur.execute("INSERT INTO scenario_referral.referral_package(ref_no,doc_type,mutual_recognition) VALUES(%s,%s,%s)", (ref, doc, mr))
            for i, (doc, seq) in enumerate([("转诊路径确认书", 1), ("费用及报销告知书", 2), ("个人健康信息授权书", 3), ("跨机构数据共享授权", 4)]):
                signed = i < 2  # 前两份已签，后两份待签（可在 UI 补签）
                cur.execute(
                    """INSERT INTO scenario_referral.referral_consent(ref_no,doc_name,seq,signed,signed_at,signer)
                       VALUES(%s,%s,%s,%s, CASE WHEN %s THEN now() ELSE NULL END, CASE WHEN %s THEN 'uliming' ELSE NULL END)""",
                    (ref, doc, seq, signed, signed, signed),
                )
            for seq, (title, detail) in enumerate(
                [("首诊评估完成", "李明医生完成评估，风险分层"), ("转诊申请已提交", "智能推荐匹配温州市中心医院心内科"), ("接收医院待确认", "号源 06-19 14:30 预锁定")], 1
            ):
                cur.execute("INSERT INTO scenario_referral.referral_track(ref_no,seq,title,detail,operator) VALUES(%s,%s,%s,%s,'uliming')", (ref, seq, title, detail))

        # ---- 机构分账 / 异常预警 / MDT ----
        cur.execute("DELETE FROM scenario_referral.org_settlement WHERE period='2026-06'")
        for org, svc, bonus, alloc in [("wtsc", 38200, 2800, 41000), ("wzcvh", 42560, 1100, 43660), ("nhsc", 18320, 600, 18920)]:
            cur.execute("INSERT INTO scenario_referral.org_settlement(org_id,period,service_amount,quality_bonus,actual_alloc) VALUES(%s,'2026-06',%s,%s,%s)", (org, svc, bonus, alloc))
        cur.execute("DELETE FROM scenario_referral.referral_alert")
        for lvl, cat, title, detail in [
            ("p1", "超时", "急危重症响应超时", "ZZ-00118 已等待2小时12分，超出15分钟时限"),
            ("p2", "费用异常", "医保费用异常", "李*华 温医大附一院 ¥45,200 超均值183%"),
            ("p3", "重复检查", "重复检查预警", "本月可互认未互认127例，预计浪费¥31,750"),
        ]:
            cur.execute("INSERT INTO scenario_referral.referral_alert(level,category,title,detail) VALUES(%s,%s,%s,%s)", (lvl, cat, title, detail))
        cur.execute("DELETE FROM scenario_referral.mdt_opinion")
        cur.execute("DELETE FROM scenario_referral.mdt_expert")
        cur.execute("DELETE FROM scenario_referral.mdt_session")
        cur.execute(
            """INSERT INTO scenario_referral.mdt_session(ref_no,topic,case_summary,status,host_user,org_id,dept_code)
               VALUES('EXT-001','疑难胸痛 MDT','男57岁反复胸闷2月，社区心电图ST压低，合并2型糖尿病8年HbA1c8.2%','scheduled','uwmy','wzcvh','card')
               RETURNING id"""
        )
        mdt_id = cur.fetchone()[0]
        for name, dept, org, role, conf in [
            ("王明远", "心血管内科", "市中心医院", "主持", True),
            ("李慧", "影像科", "市中心医院", "参与", True),
            ("张强", "内分泌科", "市中心医院", "参与", False),
        ]:
            cur.execute("INSERT INTO scenario_referral.mdt_expert(mdt_id,name,dept,org,role,confirmed) VALUES(%s,%s,%s,%s,%s,%s)", (mdt_id, name, dept, org, role, conf))

        # ---- 健康档案（platform_archive）----
        apats = ["P-1001", "P-1002"]
        cur.execute("DELETE FROM platform_archive.prescription_item WHERE rx_id IN (SELECT rx_id FROM platform_archive.prescription WHERE patient_id = ANY(%s))", (apats,))
        for _t in ("prescription", "report", "diagnosis", "encounter"):
            cur.execute(f"DELETE FROM platform_archive.{_t} WHERE patient_id = ANY(%s)", (apats,))
        cur.executemany(
            "INSERT INTO platform_archive.encounter(encounter_id,patient_id,org_id,dept_code,type,visit_time,doctor_id,chief_complaint) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            [
                ("ENC-1001-1", "P-1001", "wtsc", "gp_wt", "门诊", "2026-06-10 09:20+08", "uliming", "胸痛、胸闷反复发作3个月，加重1周"),
                ("ENC-1001-2", "P-1001", "wzcvh", "card", "门诊", "2026-05-28 10:10+08", "uwmy", "心内科复诊"),
                ("ENC-1002-1", "P-1002", "wzcvh", "endo", "门诊", "2026-06-05 14:00+08", "u1", "血糖控制不佳"),
            ],
        )
        cur.executemany(
            "INSERT INTO platform_archive.diagnosis(patient_id,encounter_id,icd_code,name,is_chronic) VALUES(%s,%s,%s,%s,%s)",
            [
                ("P-1001", "ENC-1001-1", "I25.1", "冠状动脉粥样硬化性心脏病", True),
                ("P-1001", "ENC-1001-1", "E11", "2型糖尿病", True),
                ("P-1002", "ENC-1002-1", "E11", "2型糖尿病", True),
            ],
        )
        cur.executemany(
            "INSERT INTO platform_archive.report(report_id,patient_id,encounter_id,category,item_name,conclusion,report_time,org_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            [
                ("REP-1001-1", "P-1001", "ENC-1001-1", "检验", "血常规", "未见明显异常", "2026-06-10 11:00+08", "wtsc"),
                ("REP-1001-2", "P-1001", "ENC-1001-1", "影像", "胸部CT平扫", "冠状动脉钙化，建议进一步评估", "2026-06-11 09:00+08", "wtsc"),
                ("REP-1001-3", "P-1001", "ENC-1001-1", "影像", "心脏彩超", "LVEF 58%，左室舒张功能减低", "2026-06-11 10:00+08", "wtsc"),
                ("REP-1001-4", "P-1001", "ENC-1001-1", "功能", "24h动态心电图", "偶发室性早搏", "2026-06-09 16:00+08", "wtsc"),
                ("REP-1001-5", "P-1001", "ENC-1001-1", "检验", "心肌酶谱", "正常范围", "2026-06-10 11:00+08", "wtsc"),
                ("REP-1002-1", "P-1002", "ENC-1002-1", "检验", "糖化血红蛋白", "HbA1c 8.1%", "2026-06-05 15:00+08", "wzcvh"),
            ],
        )
        cur.execute("INSERT INTO platform_archive.prescription(rx_id,patient_id,encounter_id,status,doctor_id) VALUES('RX-1001-1','P-1001','ENC-1001-2','issued','uwmy')")
        cur.executemany(
            "INSERT INTO platform_archive.prescription_item(rx_id,drug_name,usage,course) VALUES(%s,%s,%s,%s)",
            [("RX-1001-1", "阿司匹林肠溶片 100mg", "qd 口服", "长期"), ("RX-1001-1", "阿托伐他汀钙 20mg", "qn 口服", "长期")],
        )
        # 转诊资料包的可互认项关联真实报告（资料互认引用真档案）
        for doc, rep in [("血常规", "REP-1001-1"), ("胸部CT平扫", "REP-1001-2"), ("心脏彩超", "REP-1001-3")]:
            cur.execute("UPDATE scenario_referral.referral_package SET source_report_id=%s WHERE ref_no='EXT-001' AND doc_type=%s", (rep, doc))

        # ---- 场景006 在线复诊（复用平台清分）----
        cur.execute(
            """INSERT INTO platform_clearing.service_rate_card(scenario_code,service_type,applies_org_tier,applies_title_rank,unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio,status)
               SELECT 'scenario-006','online_consult','any',0,30.00,0.70,0.10,0.10,0.10,'active'
               WHERE NOT EXISTS(SELECT 1 FROM platform_clearing.service_rate_card WHERE service_type='online_consult')"""
        )
        cur.execute("DELETE FROM scenario_teleconsult.consult_rx WHERE consult_no LIKE 'TC-%'")
        cur.execute("DELETE FROM scenario_teleconsult.consult WHERE consult_no LIKE 'TC-%'")
        cur.executemany(
            "INSERT INTO scenario_teleconsult.consult(consult_no,patient_id,status,chief_complaint,ai_triage,org_id,dept_code,created_by) VALUES(%s,%s,%s,%s,%s,'wzcvh','card','seed')",
            [
                ("TC-001", "P-1001", "waiting", "血压控制后复诊配药", "low"),
                ("TC-002", "P-1002", "waiting", "糖尿病复诊，血糖波动", "medium"),
            ],
        )

        # ---- 体征监测（platform_iot）----
        cur.execute("DELETE FROM platform_iot.vital_threshold")
        cur.executemany(
            "INSERT INTO platform_iot.vital_threshold(metric,low_num,high_num,unit,label) VALUES(%s,%s,%s,%s,%s)",
            [
                ("bp", 90, 140, "mmHg", "收缩压"), ("glucose", 3.9, 10.0, "mmol/L", "血糖"),
                ("spo2", 90, 100, "%", "血氧"), ("hr", 50, 100, "bpm", "心率"),
                ("temp", 36.0, 37.3, "℃", "体温"), ("weight", None, None, "kg", "体重"),
            ],
        )
        cur.execute("DELETE FROM platform_iot.vital_sign WHERE patient_id IN ('P-1003','P-1001')")
        for pid, metric, vn, vt, unit, hrs, src, ab in [
            ("P-1003", "spo2", 96, "96", "%", 10, "device", False),
            ("P-1003", "spo2", 94, "94", "%", 6, "device", False),
            ("P-1003", "spo2", 89, "89", "%", 1, "device", True),    # 血氧走低 → 预警
            ("P-1003", "bp", 145, "145/92", "mmHg", 8, "nurse", True),
            ("P-1003", "bp", 132, "132/84", "mmHg", 2, "device", False),
            ("P-1003", "hr", 78, "78", "bpm", 8, "device", False),
            ("P-1003", "hr", 104, "104", "bpm", 1, "device", True),
            ("P-1003", "glucose", 9.1, "9.1", "mmol/L", 9, "self", False),
            ("P-1001", "bp", 128, "128/82", "mmHg", 5, "self", False),
            ("P-1001", "glucose", 6.8, "6.8", "mmol/L", 5, "self", False),
        ]:
            cur.execute(
                "INSERT INTO platform_iot.vital_sign(patient_id,metric,value_num,value_text,unit,measured_at,source,abnormal_flag,org_id,dept_code) VALUES(%s,%s,%s,%s,%s, now() - (%s || ' hours')::interval, %s,%s,'wzcvh','card')",
                (pid, metric, vn, vt, unit, hrs, src, ab),
            )

        # ---- 场景002 家庭病床（复用 platform_clearing + platform_iot）----
        cur.execute(
            """INSERT INTO platform_clearing.service_rate_card(scenario_code,service_type,applies_org_tier,applies_title_rank,unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio,status)
               SELECT 'scenario-002','homebed_care','any',0,80.00,0.60,0.20,0.10,0.10,'active'
               WHERE NOT EXISTS(SELECT 1 FROM platform_clearing.service_rate_card WHERE service_type='homebed_care')"""
        )
        cur.execute("DELETE FROM scenario_homebed.bed_message WHERE bed_no LIKE 'HB-%'")
        cur.execute("DELETE FROM scenario_homebed.care_task WHERE bed_no LIKE 'HB-%'")
        cur.execute("DELETE FROM scenario_homebed.bed WHERE bed_no LIKE 'HB-%'")
        cur.execute(
            "INSERT INTO scenario_homebed.bed(bed_no,patient_id,status,care_level,attending_doctor,admit_date,org_id,dept_code,created_by) VALUES('HB-0001','P-1003','admitted','一级护理','uwmy', CURRENT_DATE - 6, 'wzcvh','card','seed')"
        )
        cur.executemany(
            "INSERT INTO scenario_homebed.care_task(bed_no,type,content,status,assignee) VALUES('HB-0001',%s,%s,%s,'nurse01')",
            [("体征采集", "每日2次血氧/血压采集", "todo"), ("查房", "视频查房评估血氧波动", "todo"), ("送药", "氨氯地平配送上门", "done")],
        )
        cur.executemany(
            "INSERT INTO scenario_homebed.bed_message(bed_no,sender,sender_role,content) VALUES('HB-0001',%s,%s,%s)",
            [("P-1003", "patient", "昨晚感觉有点气促，血氧好像低了"), ("uwmy", "doctor", "已收到，已安排今晚加密监测，注意休息，有不适随时联系")],
        )

        # ---- 真库认证：角色/密码/数据权限/场景授权/监护关系（platform-auth 不再硬编码）----
        h123 = hashlib.sha256(b"123456").hexdigest()
        hadm = hashlib.sha256(b"admin123").hexdigest()
        cur.executemany(
            "INSERT INTO platform_identity.role(role_code,name,builtin) VALUES(%s,%s,true) ON CONFLICT(role_code) DO NOTHING",
            [("doctor", "医生"), ("nurse", "护士"), ("admin", "管理员"), ("resident", "居民"), ("regulator", "监管")],
        )
        cur.execute(
            "INSERT INTO platform_identity.app_user(user_id,username,name,password_hash,source,user_type,org_id,status) VALUES('pt_zjg','patient_zjg','张建国',%s,'local','resident','wzcvh','active') ON CONFLICT(user_id) DO UPDATE SET password_hash=EXCLUDED.password_hash,username=EXCLUDED.username,user_type=EXCLUDED.user_type",
            (h123,),
        )
        cur.execute("UPDATE platform_identity.app_user SET password_hash=%s WHERE user_id='u1'", (h123,))
        cur.execute("UPDATE platform_identity.app_user SET password_hash=%s WHERE user_id='u0'", (hadm,))
        cur.execute("DELETE FROM platform_identity.user_role WHERE user_id IN ('u1','u0','pt_zjg','uwmy','uliming')")
        cur.executemany(
            "INSERT INTO platform_identity.user_role(user_id,role_code) VALUES(%s,%s)",
            [("u1", "doctor"), ("u0", "admin"), ("pt_zjg", "resident"), ("uwmy", "doctor"), ("uliming", "doctor")],
        )
        cur.execute("DELETE FROM platform_identity.user_data_scope WHERE user_id IN ('u1','u0','uwmy','uliming')")
        cur.executemany(
            "INSERT INTO platform_identity.user_data_scope(user_id,scope_type,dept_code) VALUES(%s,%s,%s)",
            [("u1", "custom", "card"), ("u0", "all", None), ("uwmy", "custom", "card"), ("uliming", "custom", "gp_wt")],
        )
        cur.executemany(
            "INSERT INTO platform_identity.scenario_registry(scenario_code,name,status) VALUES(%s,%s,'online') ON CONFLICT(scenario_code) DO NOTHING",
            [("referral", "转诊一件事"), ("teleconsult", "在线复诊"), ("homebed", "家庭病床")],
        )
        cur.execute("DELETE FROM platform_identity.enrollment_capability WHERE enrollment_id IN (SELECT enrollment_id FROM platform_identity.staff_scenario_enrollment WHERE user_id='u1')")
        cur.execute("DELETE FROM platform_identity.staff_scenario_enrollment WHERE user_id='u1'")
        for scen, srole, caps in [
            ("referral", "接收医师", ["referral:receive", "referral:initiate"]),
            ("teleconsult", "接诊医师", ["teleconsult:treat"]),
            ("homebed", "管床医师", ["homebed:manage"]),
        ]:
            cur.execute("INSERT INTO platform_identity.staff_scenario_enrollment(user_id,scenario_code,scenario_role,status) VALUES('u1',%s,%s,'active') RETURNING enrollment_id", (scen, srole))
            eid = cur.fetchone()[0]
            for cap in caps:
                cur.execute("INSERT INTO platform_identity.enrollment_capability(enrollment_id,cap_code,granted) VALUES(%s,%s,true)", (eid, cap))
        cur.execute("DELETE FROM platform_identity.patient_guardian WHERE guardian_user_id='pt_zjg'")
        cur.execute("INSERT INTO platform_identity.patient_guardian(patient_id,guardian_user_id,relation) VALUES('P-1001','pt_zjg','本人')")

        # ---- 数据授权 + 文件元数据 ----
        cur.execute("DELETE FROM platform_consent.consent_record WHERE patient_id='P-1001'")
        cur.executemany(
            "INSERT INTO platform_consent.consent_record(patient_id,grantee,grantee_name,purpose,scope,status,evidence_hash,updated_by) VALUES('P-1001',%s,%s,%s,%s,'granted',%s,'pt_zjg')",
            [("ai_assistant", "AI健康助手", "个性化健康建议", "健康档案", "h1"), ("insurer", "带病体商保", "保费优惠核算", "依从数据", "h2")],
        )
        cur.execute("INSERT INTO platform_consent.consent_record(patient_id,grantee,grantee_name,purpose,scope,status,revoked_at,evidence_hash,updated_by) VALUES('P-1001','research','XXX-301临床研究','真实世界研究','匿名化数据','revoked', now(), 'h3','pt_zjg')")
        cur.execute("DELETE FROM platform_file.file_object WHERE patient_id='P-1001'")
        cur.executemany(
            "INSERT INTO platform_file.file_object(file_id,filename,mime,size_bytes,sha256,storage_uri,owner_user_id,patient_id,dept_code,scenario) VALUES(%s,%s,%s,%s,%s,%s,'uwmy','P-1001','card',%s)",
            [
                ("F-rep1001ct", "胸部CT平扫报告.pdf", "application/pdf", 284512, "abc123", "minio://hospital/F-rep1001ct", "archive"),
                ("F-rxsign", "转诊知情同意签署.pdf", "application/pdf", 51200, "def456", "minio://hospital/F-rxsign", "referral"),
            ],
        )

        # ---- 场景001 在线随访（随访计划 + 随访记录）----
        cur.execute("DELETE FROM scenario_followup.followup_record WHERE dept_code='card'")
        cur.execute("DELETE FROM scenario_followup.followup_plan WHERE dept_code='card'")
        cur.execute(
            """INSERT INTO scenario_followup.followup_plan
               (plan_no,patient_id,dept_code,org_id,plan_type,interval_days,start_date,note,created_by,updated_by)
               VALUES('FP-0001','P-1001','card','wzcvh','chronic',30,CURRENT_DATE-90,'冠心病术后慢病随访管理','seed','seed')
               ON CONFLICT(plan_no) DO NOTHING"""
        )
        cur.executemany(
            """INSERT INTO scenario_followup.followup_record
               (patient_id,dept_code,org_id,plan_no,visit_date,method,note,next_date,doctor_id,created_by,updated_by)
               VALUES(%s,'card','wzcvh','FP-0001',%s,%s,%s,%s,'u1','seed','seed')""",
            [
                ("P-1001", "2026-05-12", "phone", "血压140/90，症状平稳，继续当前用药方案", "2026-06-12"),
                ("P-1001", "2026-06-12", "video", "血压135/85，患者反映偶有头晕，建议增加血压监测频次", "2026-07-12"),
                ("P-1002", "2026-05-20", "phone", "血糖6.8 mmol/L（空腹），控制较好，继续原方案", "2026-06-20"),
                ("P-1002", "2026-06-18", "onsite", "血糖7.2 mmol/L，HbA1c 6.9%，轻度升高，调整二甲双胍剂量", "2026-07-18"),
            ],
        )
        # 注册场景001到 scenario_registry（如表存在）
        cur.execute(
            "INSERT INTO platform_identity.scenario_registry(scenario_code,name,status) VALUES('followup','在线随访','online') ON CONFLICT(scenario_code) DO NOTHING"
        )

        conn.commit()

        # 汇总
        report = {
            "机构": "platform_identity.organization",
            "科室": "platform_identity.department",
            "医护": "platform_identity.staff_profile",
            "多点执业": "platform_identity.staff_affiliation",
            "资质证照": "platform_identity.staff_credential",
            "患者(加密)": "platform_patient.patient",
            "参保": "platform_insurance.patient_insurance",
            "报销规则": "platform_insurance.insurance_policy_rule",
            "检查互认目录": "platform_dict.mutual_recognition_catalog",
            "号源": "platform_appointment.appointment_slot",
            "转诊单": "scenario_referral.referral",
            "就诊": "platform_archive.encounter",
            "诊断": "platform_archive.diagnosis",
            "报告": "platform_archive.report",
            "处方": "platform_archive.prescription",
            "在线复诊": "scenario_teleconsult.consult",
            "体征": "platform_iot.vital_sign",
            "家庭病床": "scenario_homebed.bed",
            "随访记录": "scenario_followup.followup_record",
            "数据授权": "platform_consent.consent_record",
            "文件": "platform_file.file_object",
        }
        print("== 外部源数据已灌入 ==")
        for label, tbl in report.items():
            cur.execute(f"SELECT count(*) FROM {tbl}")
            print(f"  {label:<12} {cur.fetchone()[0]} 行  ({tbl})")


if __name__ == "__main__":
    main()
