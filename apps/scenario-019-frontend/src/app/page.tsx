"use client";

import { AuthGate, Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type ReferralOut,
  type ReceiveOut,
  type NodeStatusOut,
  type AccountOut,
  type ReferralCreateIn,
  listReferrals,
  createReferral,
  receiveReferral,
  listNodes,
  completeNode,
  getCreditAccount,
} from "./referral-api";
import MdtView from "./MdtView";

type Tab = "referral" | "mdt";

export default function Page() {
  return (
    <AuthGate title="场景019 · 转诊一件事">
      <PageInner />
    </AuthGate>
  );
}

function PageInner() {
  const [tab, setTab] = useState<Tab>("referral");
  return (
    <main style={{ padding: 24, maxWidth: 1200 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 4 }}>
        <h1 style={{ margin: 0 }}>场景 019 · 转诊一件事</h1>
      </div>
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #f0f0f0", marginBottom: 20 }}>
        {([["referral", "🔁 转诊协同"], ["mdt", "👥 MDT 会诊"]] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "10px 18px", border: "none", background: "none", cursor: "pointer",
              fontSize: 15, color: tab === t ? "#1677ff" : "#595959",
              borderBottom: tab === t ? "2px solid #1677ff" : "2px solid transparent",
              fontWeight: tab === t ? 600 : 400,
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "referral" ? <ReferralView /> : <MdtView />}
    </main>
  );
}

const STATUS_LABEL: Record<string, string> = {
  applying: "申请中",
  received: "已接收",
  completed: "已完成",
  cancelled: "已取消",
};

const STATUS_COLOR: Record<string, string> = {
  applying: "#d46b08",
  received: "#1677ff",
  completed: "#389e0d",
  cancelled: "#8c8c8c",
};

const RISK_LABEL: Record<string, string> = {
  red: "高风险",
  yellow: "中风险",
  green: "低风险",
  critical: "危急",
};

const RISK_COLOR: Record<string, string> = {
  red: "#cf1322",
  yellow: "#d46b08",
  green: "#389e0d",
  critical: "#722ed1",
};

const NODE_LABEL: Record<string, string> = {
  first_visit: "首诊评估",
  package: "资料打包",
  apply: "转诊申请",
  accept: "接收确认",
  downward_plan: "下转方案",
  continue: "接续确认",
  followup: "随访执行",
};

const PAYEE_LABEL: Record<string, string> = {
  individual: "医生个人",
  dept: "科室",
  org: "机构",
  platform: "平台",
};

function ReferralView() {
  const [referrals, setReferrals] = useState<ReferralOut[]>([]);
  const [selected, setSelected] = useState<ReferralOut | null>(null);
  const [receiveResult, setReceiveResult] = useState<ReceiveOut | null>(null);
  const [nodes, setNodes] = useState<NodeStatusOut[]>([]);
  const [account, setAccount] = useState<AccountOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  // 发起转诊表单
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<ReferralCreateIn>({
    patient_id: "",
    type: "up",
    risk_level: "yellow",
  });
  const [creating, setCreating] = useState(false);

  async function loadAll() {
    setLoading(true);
    setError(undefined);
    try {
      const [list, acct] = await Promise.all([listReferrals(), getCreditAccount()]);
      setReferrals(list);
      setAccount(acct);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function selectRef(ref: ReferralOut) {
    setSelected(ref);
    setReceiveResult(null);
    setError(undefined);
    try {
      const nodeList = await listNodes(ref.ref_no);
      setNodes(nodeList);
    } catch {
      setNodes([]);
    }
  }

  async function handleReceive() {
    if (!selected) return;
    setError(undefined);
    try {
      const result = await receiveReferral(selected.ref_no);
      setReceiveResult(result);
      setSelected({ ...selected, status: "received" });
      await loadAll();
      const nodeList = await listNodes(selected.ref_no);
      setNodes(nodeList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "接收失败");
    }
  }

  async function handleCompleteNode(ref_no: string, node: string) {
    setError(undefined);
    try {
      await completeNode(ref_no, node);
      const nodeList = await listNodes(ref_no);
      setNodes(nodeList);
      const acct = await getCreditAccount();
      setAccount(acct);
    } catch (e) {
      setError(e instanceof Error ? e.message : "节点完成失败");
    }
  }

  async function handleCreate() {
    if (!createForm.patient_id.trim()) return;
    setCreating(true);
    setError(undefined);
    try {
      await createReferral(createForm);
      setShowCreate(false);
      setCreateForm({ patient_id: "", type: "up", risk_level: "yellow" });
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "发起转诊失败");
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  const doneCount = nodes.filter((n) => n.done).length;
  const totalPoints = nodes.filter((n) => n.done).reduce((s, n) => s + n.points, 0);

  return (
    <div>
      {/* 工具栏 */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <Button onClick={loadAll}>刷新</Button>
        <Button onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "+ 发起转诊"}
        </Button>
        {account && (
          <div
            style={{
              marginLeft: "auto",
              padding: "6px 14px",
              background: "#f0f5ff",
              borderRadius: 20,
              fontSize: 13,
              color: "#2f54eb",
            }}
          >
            服务信用：{account.points} 分 · ¥{account.balance.toFixed(2)}
          </div>
        )}
      </div>

      {error && <p style={{ color: "#d4380d", marginBottom: 16 }}>错误：{error}</p>}
      {loading && <p style={{ color: "#1677ff" }}>加载中…</p>}

      {/* 发起转诊表单 */}
      {showCreate && (
        <Card title="发起转诊" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 12, alignItems: "end" }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                患者 ID *
              </label>
              <input
                value={createForm.patient_id}
                onChange={(e) => setCreateForm({ ...createForm, patient_id: e.target.value })}
                placeholder="如：P-1001"
                style={{
                  width: "100%", padding: "6px 10px", border: "1px solid #d9d9d9",
                  borderRadius: 6, fontSize: 14, boxSizing: "border-box",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                转诊类型
              </label>
              <select
                value={createForm.type}
                onChange={(e) => setCreateForm({ ...createForm, type: e.target.value })}
                style={{
                  width: "100%", padding: "6px 10px", border: "1px solid #d9d9d9",
                  borderRadius: 6, fontSize: 14, boxSizing: "border-box",
                }}
              >
                <option value="up">上转</option>
                <option value="down">下转</option>
                <option value="flat">平转</option>
                <option value="emergency">急诊</option>
                <option value="mdt">MDT</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                风险等级
              </label>
              <select
                value={createForm.risk_level}
                onChange={(e) => setCreateForm({ ...createForm, risk_level: e.target.value })}
                style={{
                  width: "100%", padding: "6px 10px", border: "1px solid #d9d9d9",
                  borderRadius: 6, fontSize: 14, boxSizing: "border-box",
                }}
              >
                <option value="green">低风险</option>
                <option value="yellow">中风险</option>
                <option value="red">高风险</option>
                <option value="critical">危急</option>
              </select>
            </div>
            <Button
              onClick={handleCreate}
              disabled={!createForm.patient_id.trim() || creating}
            >
              {creating ? "提交中…" : "提交"}
            </Button>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1.2fr" : "1fr", gap: 20 }}>
        {/* 转诊单列表 */}
        <div>
          <h2 style={{ marginTop: 0 }}>转诊单列表（{referrals.length}）</h2>
          {referrals.length === 0 && !loading && (
            <p style={{ color: "#8c8c8c" }}>暂无转诊单</p>
          )}
          <div style={{ display: "grid", gap: 10 }}>
            {referrals.map((r) => (
              <Card
                key={r.ref_no}
                title={r.ref_no}
                onClick={() => selectRef(r)}
                style={{
                  cursor: "pointer",
                  border: selected?.ref_no === r.ref_no ? "2px solid #1677ff" : undefined,
                }}
              >
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
                  <span
                    style={{
                      background: `${RISK_COLOR[r.risk_level] ?? "#595959"}18`,
                      color: RISK_COLOR[r.risk_level] ?? "#595959",
                      padding: "1px 8px",
                      borderRadius: 10,
                      fontWeight: 600,
                    }}
                  >
                    {RISK_LABEL[r.risk_level] ?? r.risk_level}
                  </span>
                  <span style={{ color: STATUS_COLOR[r.status] ?? "#333" }}>
                    {STATUS_LABEL[r.status] ?? r.status}
                  </span>
                  <span style={{ color: "#8c8c8c" }}>患者：{r.patient_id}</span>
                  <span style={{ color: "#8c8c8c" }}>科室：{r.dept_code}</span>
                  <span style={{ color: "#8c8c8c" }}>{r.type === "up" ? "上转" : r.type === "down" ? "下转" : r.type}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 转诊详情 */}
        {selected && (
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <h2 style={{ margin: 0 }}>{selected.ref_no}</h2>
              <button
                onClick={() => { setSelected(null); setReceiveResult(null); setNodes([]); }}
                style={{ fontSize: 12, cursor: "pointer", color: "#8c8c8c", background: "none", border: "none" }}
              >
                关闭
              </button>
            </div>

            {/* 基本信息 */}
            <Card title="转诊信息">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                <div><span style={{ color: "#8c8c8c" }}>患者 ID：</span>{selected.patient_id}</div>
                <div><span style={{ color: "#8c8c8c" }}>科室：</span>{selected.dept_code}</div>
                <div>
                  <span style={{ color: "#8c8c8c" }}>风险等级：</span>
                  <span style={{ color: RISK_COLOR[selected.risk_level], fontWeight: 600 }}>
                    {RISK_LABEL[selected.risk_level] ?? selected.risk_level}
                  </span>
                </div>
                <div>
                  <span style={{ color: "#8c8c8c" }}>状态：</span>
                  <span style={{ color: STATUS_COLOR[selected.status] }}>
                    {STATUS_LABEL[selected.status] ?? selected.status}
                  </span>
                </div>
                <div><span style={{ color: "#8c8c8c" }}>类型：</span>{selected.type}</div>
              </div>

              {selected.status === "applying" && (
                <div style={{ marginTop: 14 }}>
                  <Button onClick={handleReceive}>接收转诊</Button>
                </div>
              )}
            </Card>

            {/* 4方分账结果 */}
            {receiveResult && (
              <Card
                title={`接收成功 · 分账明细（合计 ¥${receiveResult.gross_amount.toFixed(2)}）`}
                style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}
              >
                <div style={{ display: "grid", gap: 6 }}>
                  {receiveResult.splits.map((s) => (
                    <div
                      key={s.payee_type}
                      style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}
                    >
                      <span style={{ color: "#595959" }}>
                        {PAYEE_LABEL[s.payee_type] ?? s.payee_type}
                        <span style={{ color: "#8c8c8c", marginLeft: 6 }}>({s.payee_id})</span>
                      </span>
                      <strong>¥{s.amount.toFixed(2)}</strong>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* 七节点进度 */}
            {nodes.length > 0 && (
              <Card
                title={`七节点进度（${doneCount}/7 完成 · 已得 ${totalPoints} 分）`}
              >
                <div style={{ display: "grid", gap: 8 }}>
                  {nodes.map((n) => (
                    <div
                      key={n.node}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "8px 10px",
                        background: n.done ? "#f6ffed" : "#fafafa",
                        borderRadius: 6,
                        border: `1px solid ${n.done ? "#b7eb8f" : "#f0f0f0"}`,
                      }}
                    >
                      <span style={{ fontSize: 16 }}>{n.done ? "✓" : "○"}</span>
                      <span style={{ flex: 1, fontSize: 13 }}>
                        {NODE_LABEL[n.node] ?? n.node}
                      </span>
                      <span
                        style={{
                          fontSize: 12,
                          color: n.done ? "#389e0d" : "#8c8c8c",
                          minWidth: 40,
                          textAlign: "right",
                        }}
                      >
                        {n.points} 分
                      </span>
                      {!n.done && (
                        <button
                          onClick={() => handleCompleteNode(selected.ref_no, n.node)}
                          style={{
                            fontSize: 12,
                            padding: "2px 10px",
                            border: "1px solid #d9d9d9",
                            borderRadius: 4,
                            cursor: "pointer",
                            background: "#fff",
                          }}
                        >
                          完成
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* 信用账户 */}
            {account && (
              <Card title="我的服务信用账户">
                <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: "#2f54eb" }}>
                      {account.points}
                    </div>
                    <div style={{ fontSize: 12, color: "#8c8c8c" }}>累计积分</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: "#389e0d" }}>
                      ¥{account.balance.toFixed(2)}
                    </div>
                    <div style={{ fontSize: 12, color: "#8c8c8c" }}>可兑现金额</div>
                  </div>
                </div>
                {account.ledger.length > 0 && (
                  <div style={{ display: "grid", gap: 4 }}>
                    {account.ledger.slice(-5).map((item, i) => (
                      <div
                        key={i}
                        style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#595959" }}
                      >
                        <span>{NODE_LABEL[item.node] ?? item.node}</span>
                        <span>{item.points} 分 · ¥{item.earned.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
