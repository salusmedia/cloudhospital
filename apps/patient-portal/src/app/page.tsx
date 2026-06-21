"use client";

import { Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type ConsultOut,
  type ReferralOut,
  type NodeStatusOut,
  type FollowupRecordOut,
  login,
  listMyConsults,
  createConsult,
  listMyReferrals,
  listReferralNodes,
  listMyFollowups,
} from "./patient-api";

const STATUS_LABEL: Record<string, string> = {
  waiting: "候诊中", in_progress: "就诊中", finished: "已完成",
  applying: "申请中", received: "已接收", completed: "已完成", cancelled: "已取消",
};

const STATUS_COLOR: Record<string, string> = {
  waiting: "#d46b08", in_progress: "#1677ff", finished: "#8c8c8c",
  applying: "#d46b08", received: "#1677ff", completed: "#389e0d", cancelled: "#8c8c8c",
};

const RISK_LABEL: Record<string, string> = {
  red: "高风险", yellow: "中风险", green: "低风险", critical: "危急",
};

const RISK_COLOR: Record<string, string> = {
  red: "#cf1322", yellow: "#d46b08", green: "#389e0d", critical: "#722ed1",
};

const NODE_LABEL: Record<string, string> = {
  first_visit: "首诊评估", package: "资料打包", apply: "转诊申请",
  accept: "接收确认", downward_plan: "下转方案", continue: "接续确认", followup: "随访执行",
};

const METHOD_LABEL: Record<string, string> = {
  phone: "电话随访", video: "视频随访", onsite: "面访",
};

type Tab = "consult" | "referral" | "followup";

export default function Page() {
  const [token, setToken] = useState<string | null>(null);
  const [userName, setUserName] = useState("");
  const [loginUser, setLoginUser] = useState("patient_zjg");
  const [loginPass, setLoginPass] = useState("123456");
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  const [tab, setTab] = useState<Tab>("consult");
  const [consults, setConsults] = useState<ConsultOut[]>([]);
  const [referrals, setReferrals] = useState<ReferralOut[]>([]);
  const [followups, setFollowups] = useState<FollowupRecordOut[]>([]);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [refNodes, setRefNodes] = useState<NodeStatusOut[]>([]);
  const [error, setError] = useState<string>();

  // 发起复诊
  const [complaint, setComplaint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<ConsultOut | null>(null);

  async function handleLogin() {
    setLoggingIn(true);
    setLoginError("");
    try {
      const out = await login(loginUser, loginPass);
      localStorage.setItem("token", out.token);
      setToken(out.token);
      setUserName(out.name);
      loadAll();
    } catch {
      setLoginError("账号或密码错误");
    } finally {
      setLoggingIn(false);
    }
  }

  async function loadAll() {
    setError(undefined);
    try {
      const [c, r, f] = await Promise.all([
        listMyConsults(),
        listMyReferrals(),
        listMyFollowups(),
      ]);
      setConsults(c);
      setReferrals(r);
      setFollowups(f);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  async function selectReferral(ref_no: string) {
    setSelectedRef(ref_no);
    try {
      const nodes = await listReferralNodes(ref_no);
      setRefNodes(nodes);
    } catch {
      setRefNodes([]);
    }
  }

  async function handleCreateConsult() {
    if (!complaint.trim()) return;
    setSubmitting(true);
    setError(undefined);
    try {
      const c = await createConsult(complaint);
      setSubmitted(c);
      setComplaint("");
      const updated = await listMyConsults();
      setConsults(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发起失败");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    const t = localStorage.getItem("token");
    if (t) { setToken(t); loadAll(); }
  }, []);

  // ---- 登录页 ----
  if (!token) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ background: "#fff", borderRadius: 12, padding: 40, width: 340, boxShadow: "0 4px 24px #0001" }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ fontSize: 32 }}>🏥</div>
            <h2 style={{ margin: "8px 0 4px" }}>AI云医院</h2>
            <p style={{ color: "#8c8c8c", margin: 0, fontSize: 13 }}>居民健康门户</p>
          </div>
          {loginError && <p style={{ color: "#cf1322", fontSize: 13, marginBottom: 12 }}>{loginError}</p>}
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>账号</label>
              <input
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", border: "1px solid #d9d9d9", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>密码</label>
              <input
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                style={{ width: "100%", padding: "8px 12px", border: "1px solid #d9d9d9", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <Button onClick={handleLogin} disabled={loggingIn}>
              {loggingIn ? "登录中…" : "登录"}
            </Button>
          </div>
          <p style={{ color: "#8c8c8c", fontSize: 12, textAlign: "center", marginTop: 16 }}>
            演示账号：patient_zjg / 123456
          </p>
        </div>
      </main>
    );
  }

  // ---- 主界面 ----
  return (
    <main style={{ minHeight: "100vh" }}>
      {/* 顶栏 */}
      <header style={{
        background: "#1677ff", color: "#fff", padding: "0 24px",
        display: "flex", alignItems: "center", height: 56, gap: 16,
      }}>
        <span style={{ fontSize: 20 }}>🏥</span>
        <span style={{ fontWeight: 600, fontSize: 16 }}>AI云医院 · 居民健康门户</span>
        <span style={{ marginLeft: "auto", fontSize: 13, opacity: 0.85 }}>您好，{userName}</span>
        <button
          onClick={() => { localStorage.removeItem("token"); setToken(null); }}
          style={{ fontSize: 12, color: "#fff", background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 4, padding: "4px 10px", cursor: "pointer" }}
        >
          退出
        </button>
      </header>

      {/* 标签栏 */}
      <div style={{ background: "#fff", borderBottom: "1px solid #f0f0f0", padding: "0 24px", display: "flex", gap: 0 }}>
        {(["consult", "referral", "followup"] as Tab[]).map((t) => {
          const labels = { consult: "📹 我的复诊", referral: "🔁 我的转诊", followup: "📋 我的随访" };
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "14px 20px", border: "none", background: "none", cursor: "pointer",
                fontSize: 14, color: tab === t ? "#1677ff" : "#595959",
                borderBottom: tab === t ? "2px solid #1677ff" : "2px solid transparent",
                fontWeight: tab === t ? 600 : 400,
              }}
            >
              {labels[t]}
            </button>
          );
        })}
        <button
          onClick={loadAll}
          style={{ marginLeft: "auto", fontSize: 12, color: "#8c8c8c", background: "none", border: "none", cursor: "pointer", padding: "0 8px" }}
        >
          刷新
        </button>
      </div>

      <div style={{ padding: 24, maxWidth: 900 }}>
        {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}

        {/* ======== 复诊 ======== */}
        {tab === "consult" && (
          <div style={{ display: "grid", gap: 16 }}>
            {/* 发起复诊 */}
            <Card title="发起在线复诊申请">
              {submitted && (
                <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f6ffed", borderRadius: 6, border: "1px solid #b7eb8f", fontSize: 13 }}>
                  ✓ 申请已提交，诊次号：<strong>{submitted.consult_no}</strong>，请等待医生接诊
                </div>
              )}
              <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                    主诉（症状描述）*
                  </label>
                  <input
                    value={complaint}
                    onChange={(e) => setComplaint(e.target.value)}
                    placeholder="如：血压控制不佳，近期头晕"
                    style={{ width: "100%", padding: "8px 12px", border: "1px solid #d9d9d9", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
                  />
                </div>
                <Button onClick={handleCreateConsult} disabled={!complaint.trim() || submitting}>
                  {submitting ? "提交中…" : "发起复诊"}
                </Button>
              </div>
            </Card>

            {/* 复诊记录 */}
            <div>
              <h3 style={{ margin: "0 0 12px" }}>复诊记录（{consults.length}）</h3>
              {consults.length === 0
                ? <p style={{ color: "#8c8c8c" }}>暂无复诊记录</p>
                : consults.map((c) => (
                  <Card key={c.consult_no} title={c.consult_no} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", gap: 16, fontSize: 13, flexWrap: "wrap" }}>
                      <span style={{ color: STATUS_COLOR[c.status] ?? "#333", fontWeight: 600 }}>
                        {STATUS_LABEL[c.status] ?? c.status}
                      </span>
                      <span style={{ color: "#8c8c8c" }}>科室：{c.dept_code}</span>
                      {c.chief_complaint && <span>主诉：{c.chief_complaint}</span>}
                      {c.ai_triage && (
                        <span style={{
                          background: c.ai_triage === "P1" ? "#fff1f0" : "#fff7e6",
                          color: c.ai_triage === "P1" ? "#cf1322" : "#d46b08",
                          padding: "1px 8px", borderRadius: 10,
                        }}>
                          AI分诊 {c.ai_triage}
                        </span>
                      )}
                    </div>
                  </Card>
                ))
              }
            </div>
          </div>
        )}

        {/* ======== 转诊 ======== */}
        {tab === "referral" && (
          <div style={{ display: "grid", gap: 16 }}>
            <h3 style={{ margin: 0 }}>我的转诊记录（{referrals.length}）</h3>
            {referrals.length === 0
              ? <p style={{ color: "#8c8c8c" }}>暂无转诊记录</p>
              : referrals.map((r) => (
                <Card
                  key={r.ref_no}
                  title={r.ref_no}
                  onClick={() => selectReferral(r.ref_no)}
                  style={{ cursor: "pointer", border: selectedRef === r.ref_no ? "2px solid #1677ff" : undefined }}
                >
                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
                    <span style={{
                      background: `${RISK_COLOR[r.risk_level] ?? "#595959"}18`,
                      color: RISK_COLOR[r.risk_level] ?? "#595959",
                      padding: "1px 8px", borderRadius: 10, fontWeight: 600,
                    }}>
                      {RISK_LABEL[r.risk_level] ?? r.risk_level}
                    </span>
                    <span style={{ color: STATUS_COLOR[r.status] ?? "#333" }}>
                      {STATUS_LABEL[r.status] ?? r.status}
                    </span>
                    <span style={{ color: "#8c8c8c" }}>类型：{r.type === "up" ? "上转" : r.type === "down" ? "下转" : r.type}</span>
                  </div>

                  {/* 节点进度（展开显示） */}
                  {selectedRef === r.ref_no && refNodes.length > 0 && (
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f0f0f0" }}>
                      <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 8 }}>
                        七节点进度 {refNodes.filter((n) => n.done).length}/7
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                        {refNodes.map((n) => (
                          <div
                            key={n.node}
                            style={{
                              display: "flex", alignItems: "center", gap: 6, fontSize: 12,
                              color: n.done ? "#389e0d" : "#bfbfbf",
                            }}
                          >
                            <span>{n.done ? "✓" : "○"}</span>
                            <span>{NODE_LABEL[n.node] ?? n.node}</span>
                            <span style={{ marginLeft: "auto" }}>{n.points}分</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))
            }
          </div>
        )}

        {/* ======== 随访 ======== */}
        {tab === "followup" && (
          <div style={{ display: "grid", gap: 12 }}>
            <h3 style={{ margin: 0 }}>我的随访记录（{followups.length}）</h3>
            {followups.length === 0
              ? <p style={{ color: "#8c8c8c" }}>暂无随访记录</p>
              : followups.map((f) => (
                <Card key={f.id} title={`随访日期：${f.visit_date}`}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                    <div><span style={{ color: "#8c8c8c" }}>方式：</span>{METHOD_LABEL[f.method] ?? f.method}</div>
                    <div><span style={{ color: "#8c8c8c" }}>科室：</span>{f.dept_code}</div>
                    {f.note && <div style={{ gridColumn: "1/-1" }}><span style={{ color: "#8c8c8c" }}>随访备注：</span>{f.note}</div>}
                    {f.next_date && (
                      <div style={{ gridColumn: "1/-1", color: "#1677ff" }}>
                        📅 下次随访：{f.next_date}
                      </div>
                    )}
                  </div>
                </Card>
              ))
            }
          </div>
        )}
      </div>
    </main>
  );
}
