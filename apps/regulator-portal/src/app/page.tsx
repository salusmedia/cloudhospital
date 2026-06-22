"use client";

import { useEffect, useState } from "react";

import {
  type Dashboard,
  type SettlementOut,
  type RulesOut,
  type AlertOut,
  login,
  getDashboard,
  getSettlements,
  getRules,
  getAlerts,
  handleAlert,
} from "./regulator-api";

const TYPE_LABEL: Record<string, string> = {
  up: "上转", down: "下转", flat: "平转", emergency: "急诊直转", mdt: "MDT",
};

const ALERT_COLOR: Record<string, string> = {
  red: "#ff4d4f", yellow: "#faad14", green: "#52c41a",
};

const ALERT_LABEL: Record<string, string> = {
  red: "紧急", yellow: "预警", green: "提示",
};

type Tab = "dashboard" | "settlement" | "rules" | "alerts";

// ---- 深色驾驶舱样式 ----
const panel: React.CSSProperties = {
  background: "#1a2438",
  border: "1px solid #2a3650",
  borderRadius: 10,
  padding: 20,
};
const panelTitle: React.CSSProperties = {
  fontSize: 14, fontWeight: 600, color: "#8fa6cc", margin: "0 0 16px",
  textTransform: "uppercase", letterSpacing: 0.5,
};

export default function Page() {
  const [token, setToken] = useState<string | null>(null);
  const [userName, setUserName] = useState("");
  const [loginUser, setLoginUser] = useState("admin");
  const [loginPass, setLoginPass] = useState("admin123");
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  const [tab, setTab] = useState<Tab>("dashboard");
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [settle, setSettle] = useState<SettlementOut | null>(null);
  const [rules, setRules] = useState<RulesOut | null>(null);
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [error, setError] = useState<string>();

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
      const [d, s, r, a] = await Promise.all([
        getDashboard(), getSettlements(), getRules(), getAlerts(),
      ]);
      setDash(d);
      setSettle(s);
      setRules(r);
      setAlerts(a);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  async function onHandleAlert(id: string) {
    try {
      await handleAlert(id);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: "handled" } : a)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "处置失败");
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
        <div style={{ ...panel, width: 360, padding: 40 }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ fontSize: 32 }}>🛰️</div>
            <h2 style={{ margin: "8px 0 4px", color: "#e6edf7" }}>医共体监管驾驶舱</h2>
            <p style={{ color: "#5d6b85", margin: 0, fontSize: 13 }}>转诊协同 · 分账绩效 · 异常预警</p>
          </div>
          {loginError && <p style={{ color: "#ff4d4f", fontSize: 13, marginBottom: 12 }}>{loginError}</p>}
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#5d6b85", marginBottom: 4 }}>账号</label>
              <input
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                style={inputDark}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#5d6b85", marginBottom: 4 }}>密码</label>
              <input
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                style={inputDark}
              />
            </div>
            <button onClick={handleLogin} disabled={loggingIn} style={btnPrimary}>
              {loggingIn ? "登录中…" : "进入驾驶舱"}
            </button>
          </div>
          <p style={{ color: "#5d6b85", fontSize: 12, textAlign: "center", marginTop: 16 }}>
            演示账号：admin / admin123
          </p>
        </div>
      </main>
    );
  }

  const pendingAlerts = alerts.filter((a) => a.status !== "handled").length;

  // ---- 主界面 ----
  return (
    <main style={{ minHeight: "100vh", color: "#e6edf7" }}>
      {/* 顶栏 */}
      <header style={{
        background: "#131c30", borderBottom: "1px solid #2a3650",
        padding: "0 28px", display: "flex", alignItems: "center", height: 60, gap: 16,
      }}>
        <span style={{ fontSize: 22 }}>🛰️</span>
        <span style={{ fontWeight: 700, fontSize: 17 }}>医共体监管驾驶舱</span>
        <span style={{ fontSize: 12, color: "#5d6b85", marginLeft: 4 }}>全域聚合视图</span>
        <span style={{ marginLeft: "auto", fontSize: 13, color: "#8fa6cc" }}>监管员 · {userName}</span>
        <button
          onClick={() => { localStorage.removeItem("token"); setToken(null); }}
          style={{ fontSize: 12, color: "#8fa6cc", background: "#1a2438", border: "1px solid #2a3650", borderRadius: 4, padding: "5px 12px", cursor: "pointer" }}
        >
          退出
        </button>
      </header>

      {/* 标签栏 */}
      <div style={{ background: "#131c30", padding: "0 28px", display: "flex", gap: 0, borderBottom: "1px solid #2a3650" }}>
        {([
          ["dashboard", "📊 转诊监管看板"],
          ["settlement", "💰 绩效分账"],
          ["rules", "📐 规则配置"],
          ["alerts", `🚨 异常预警${pendingAlerts ? ` (${pendingAlerts})` : ""}`],
        ] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "14px 18px", border: "none", background: "none", cursor: "pointer",
              fontSize: 14, color: tab === t ? "#4d9fff" : "#8fa6cc",
              borderBottom: tab === t ? "2px solid #4d9fff" : "2px solid transparent",
              fontWeight: tab === t ? 600 : 400,
            }}
          >
            {label}
          </button>
        ))}
        <button onClick={loadAll} style={{ marginLeft: "auto", fontSize: 12, color: "#5d6b85", background: "none", border: "none", cursor: "pointer" }}>
          刷新
        </button>
      </div>

      <div style={{ padding: 28, maxWidth: 1200 }}>
        {error && <p style={{ color: "#ff4d4f" }}>错误：{error}</p>}

        {/* ======== 监管看板 ======== */}
        {tab === "dashboard" && dash && (
          <div style={{ display: "grid", gap: 20 }}>
            {/* KPI 卡片行 */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
              <KpiCard label="转诊总量" value={dash.kpi.total} unit="单" accent="#4d9fff" />
              <KpiCard label="接收率" value={(dash.kpi.received_rate * 100).toFixed(1)} unit="%" accent="#52c41a" />
              <KpiCard label="检验互认率" value={(dash.kpi.mutual_recognition_rate * 100).toFixed(1)} unit="%" accent="#13c2c2" />
              <KpiCard label="急诊直转" value={dash.kpi.emergency} unit="单" accent="#ff7a45" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* 转诊类型分布 */}
              <div style={panel}>
                <h3 style={panelTitle}>转诊类型分布</h3>
                <div style={{ display: "grid", gap: 10 }}>
                  {Object.entries(dash.type_distribution).map(([k, v]) => {
                    const max = Math.max(...Object.values(dash.type_distribution), 1);
                    return (
                      <div key={k} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ width: 64, fontSize: 13, color: "#8fa6cc" }}>{TYPE_LABEL[k] ?? k}</span>
                        <div style={{ flex: 1, background: "#0f1729", borderRadius: 4, height: 22, overflow: "hidden" }}>
                          <div style={{
                            width: `${(v / max) * 100}%`, height: "100%",
                            background: "linear-gradient(90deg,#4d9fff,#13c2c2)", borderRadius: 4,
                          }} />
                        </div>
                        <span style={{ width: 32, textAlign: "right", fontSize: 13, fontWeight: 600 }}>{v}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 接收机构排行 */}
              <div style={panel}>
                <h3 style={panelTitle}>接收机构排行 TOP5</h3>
                <div style={{ display: "grid", gap: 8 }}>
                  {dash.org_ranking.length === 0 && <p style={{ color: "#5d6b85", fontSize: 13 }}>暂无数据</p>}
                  {dash.org_ranking.map((o, i) => (
                    <div key={o.org_id} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
                      <span style={{
                        width: 22, height: 22, borderRadius: "50%", display: "flex",
                        alignItems: "center", justifyContent: "center", fontSize: 12,
                        background: i < 3 ? "#4d9fff" : "#2a3650", color: "#fff", fontWeight: 600,
                      }}>{i + 1}</span>
                      <span style={{ flex: 1 }}>{o.org_name ?? o.org_id}</span>
                      <span style={{ fontWeight: 600, color: "#4d9fff" }}>{o.inbound} 单</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======== 绩效分账 ======== */}
        {tab === "settlement" && settle && (
          <div style={{ display: "grid", gap: 20 }}>
            <div style={panel}>
              <h3 style={panelTitle}>协同服务计量</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ color: "#5d6b85", textAlign: "left" }}>
                    <th style={th}>服务项目</th>
                    <th style={{ ...th, textAlign: "right" }}>数量</th>
                    <th style={{ ...th, textAlign: "right" }}>单价(元)</th>
                    <th style={{ ...th, textAlign: "right" }}>小计(元)</th>
                  </tr>
                </thead>
                <tbody>
                  {settle.measures.map((m) => (
                    <tr key={m.name} style={{ borderTop: "1px solid #2a3650" }}>
                      <td style={td}>{m.name}</td>
                      <td style={{ ...td, textAlign: "right" }}>{m.qty}</td>
                      <td style={{ ...td, textAlign: "right" }}>{m.unit}</td>
                      <td style={{ ...td, textAlign: "right", color: "#52c41a", fontWeight: 600 }}>
                        ¥{m.subtotal.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ borderTop: "2px solid #2a3650" }}>
                    <td style={{ ...td, fontWeight: 600 }} colSpan={3}>合计</td>
                    <td style={{ ...td, textAlign: "right", color: "#52c41a", fontWeight: 700, fontSize: 15 }}>
                      ¥{settle.measures.reduce((s, m) => s + m.subtotal, 0).toLocaleString()}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={panel}>
              <h3 style={panelTitle}>机构分账明细</h3>
              {settle.org_settlements.length === 0
                ? <p style={{ color: "#5d6b85", fontSize: 13 }}>暂无机构分账记录</p>
                : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ color: "#5d6b85", textAlign: "left" }}>
                        <th style={th}>机构</th>
                        <th style={th}>周期</th>
                        <th style={{ ...th, textAlign: "right" }}>服务金额</th>
                        <th style={{ ...th, textAlign: "right" }}>质量奖励</th>
                        <th style={{ ...th, textAlign: "right" }}>实际分配</th>
                      </tr>
                    </thead>
                    <tbody>
                      {settle.org_settlements.map((o, i) => (
                        <tr key={i} style={{ borderTop: "1px solid #2a3650" }}>
                          <td style={td}>{o.org_id}</td>
                          <td style={td}>{o.period}</td>
                          <td style={{ ...td, textAlign: "right" }}>¥{Number(o.service_amount).toLocaleString()}</td>
                          <td style={{ ...td, textAlign: "right", color: "#faad14" }}>¥{Number(o.quality_bonus).toLocaleString()}</td>
                          <td style={{ ...td, textAlign: "right", color: "#52c41a", fontWeight: 600 }}>¥{Number(o.actual_alloc).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              }
            </div>
          </div>
        )}

        {/* ======== 规则配置 ======== */}
        {tab === "rules" && rules && (
          <div style={{ display: "grid", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <div style={panel}>
                <h3 style={panelTitle}>病情分层标准</h3>
                <div style={{ display: "grid", gap: 10 }}>
                  {rules.risk_layers.map((r, i) => (
                    <div key={i} style={{ padding: "10px 12px", background: "#0f1729", borderRadius: 6 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{r.level}</div>
                      <div style={{ fontSize: 12, color: "#8fa6cc" }}>{r.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={panel}>
                <h3 style={panelTitle}>时限控制</h3>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "#5d6b85", textAlign: "left" }}>
                      <th style={th}>场景</th>
                      <th style={{ ...th, textAlign: "right" }}>时限</th>
                      <th style={{ ...th, textAlign: "right" }}>预警阈值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.time_limits.map((t, i) => (
                      <tr key={i} style={{ borderTop: "1px solid #2a3650" }}>
                        <td style={td}>{t.scene}</td>
                        <td style={{ ...td, textAlign: "right", fontWeight: 600 }}>{t.limit}</td>
                        <td style={{ ...td, textAlign: "right", color: "#faad14" }}>{t.warn}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={panel}>
              <h3 style={panelTitle}>检查检验互认目录</h3>
              {rules.mutual_recognition.length === 0
                ? <p style={{ color: "#5d6b85", fontSize: 13 }}>暂无互认目录</p>
                : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 10 }}>
                    {rules.mutual_recognition.map((m, i) => (
                      <div key={i} style={{ padding: "10px 12px", background: "#0f1729", borderRadius: 6 }}>
                        <div style={{ fontSize: 12, color: "#5d6b85" }}>{m.category}</div>
                        <div style={{ fontWeight: 600, fontSize: 13, margin: "2px 0" }}>{m.item_name}</div>
                        <div style={{ fontSize: 12, color: "#8fa6cc" }}>
                          有效 {m.valid_days} 天 · {m.recognize_scope}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              }
            </div>
          </div>
        )}

        {/* ======== 异常预警 ======== */}
        {tab === "alerts" && (
          <div style={{ display: "grid", gap: 12 }}>
            {alerts.length === 0 && <p style={{ color: "#5d6b85" }}>暂无预警记录</p>}
            {alerts.map((a) => (
              <div key={a.id} style={{
                ...panel,
                padding: "14px 18px",
                borderLeft: `4px solid ${ALERT_COLOR[a.level] ?? "#5d6b85"}`,
                opacity: a.status === "handled" ? 0.55 : 1,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{
                    background: `${ALERT_COLOR[a.level] ?? "#5d6b85"}22`,
                    color: ALERT_COLOR[a.level] ?? "#5d6b85",
                    padding: "2px 10px", borderRadius: 10, fontSize: 12, fontWeight: 600,
                  }}>
                    {ALERT_LABEL[a.level] ?? a.level}
                  </span>
                  <span style={{ fontWeight: 600 }}>{a.title}</span>
                  {a.ref_no && <span style={{ fontSize: 12, color: "#5d6b85" }}>关联 {a.ref_no}</span>}
                  {a.status === "handled"
                    ? <span style={{ marginLeft: "auto", fontSize: 12, color: "#52c41a" }}>✓ 已处置</span>
                    : (
                      <button onClick={() => onHandleAlert(a.id)} style={{ ...btnSmall, marginLeft: "auto" }}>
                        处置并留痕
                      </button>
                    )
                  }
                </div>
                {a.detail && <div style={{ fontSize: 13, color: "#8fa6cc", marginTop: 8 }}>{a.detail}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function KpiCard({ label, value, unit, accent }: { label: string; value: number | string; unit: string; accent: string }) {
  return (
    <div style={{ ...panel, padding: 18 }}>
      <div style={{ fontSize: 13, color: "#5d6b85", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 30, fontWeight: 700, color: accent }}>{value}</span>
        <span style={{ fontSize: 13, color: "#8fa6cc" }}>{unit}</span>
      </div>
    </div>
  );
}

const inputDark: React.CSSProperties = {
  width: "100%", padding: "8px 12px", background: "#0f1729",
  border: "1px solid #2a3650", borderRadius: 6, fontSize: 14,
  color: "#e6edf7", boxSizing: "border-box",
};
const btnPrimary: React.CSSProperties = {
  padding: "10px", background: "#4d9fff", color: "#fff", border: "none",
  borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: "pointer",
};
const btnSmall: React.CSSProperties = {
  padding: "4px 12px", background: "#4d9fff", color: "#fff", border: "none",
  borderRadius: 4, fontSize: 12, cursor: "pointer",
};
const th: React.CSSProperties = { padding: "6px 8px", fontWeight: 500 };
const td: React.CSSProperties = { padding: "8px", color: "#e6edf7" };
