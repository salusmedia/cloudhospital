"use client";

import { AuthGate, Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type ConsultOut,
  type RxOut,
  type FinishOut,
  listConsults,
  acceptConsult,
  prescribe,
  finishConsult,
} from "./teleconsult-api";

const STATUS_LABEL: Record<string, string> = {
  waiting: "候诊中",
  in_progress: "接诊中",
  finished: "已结束",
};

const STATUS_COLOR: Record<string, string> = {
  waiting: "#d46b08",
  in_progress: "#1677ff",
  finished: "#8c8c8c",
};

const AI_REVIEW_COLOR: Record<string, string> = {
  passed: "#389e0d",
  warn: "#d46b08",
  rejected: "#cf1322",
};

const AI_REVIEW_LABEL: Record<string, string> = {
  passed: "通过",
  warn: "预警",
  rejected: "拒绝",
};

export default function Page() {
  return (
    <AuthGate title="场景006 · 在线复诊">
      <PageInner />
    </AuthGate>
  );
}

function PageInner() {
  const [consults, setConsults] = useState<ConsultOut[]>([]);
  const [selected, setSelected] = useState<ConsultOut | null>(null);
  const [rx, setRx] = useState<RxOut | null>(null);
  const [finish, setFinish] = useState<FinishOut | null>(null);
  const [drugName, setDrugName] = useState("");
  const [usage, setUsage] = useState("");
  const [prescribing, setPrescribing] = useState(false);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  async function loadConsults() {
    setLoading(true);
    setError(undefined);
    try {
      const list = await listConsults();
      setConsults(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleAccept(no: string) {
    try {
      const updated = await acceptConsult(no);
      setSelected(updated);
      setRx(null);
      setFinish(null);
      await loadConsults();
    } catch (e) {
      setError(e instanceof Error ? e.message : "接诊失败");
    }
  }

  async function handlePrescribe() {
    if (!selected || !drugName.trim()) return;
    setPrescribing(true);
    setError(undefined);
    try {
      const result = await prescribe(selected.consult_no, drugName, usage || undefined);
      setRx(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "开方失败");
    } finally {
      setPrescribing(false);
    }
  }

  async function handleFinish() {
    if (!selected) return;
    try {
      const result = await finishConsult(selected.consult_no);
      setFinish(result);
      setSelected(null);
      await loadConsults();
    } catch (e) {
      setError(e instanceof Error ? e.message : "结束失败");
    }
  }

  function selectConsult(c: ConsultOut) {
    setSelected(c);
    setRx(null);
    setFinish(null);
    setDrugName("");
    setUsage("");
    setError(undefined);
  }

  useEffect(() => {
    loadConsults();
  }, []);

  return (
    <main style={{ padding: 24, display: "grid", gap: 20, maxWidth: 1100 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <h1 style={{ margin: 0 }}>场景 006 · 在线复诊</h1>
        <Button onClick={loadConsults}>刷新</Button>
      </div>

      {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}
      {loading && <p style={{ color: "#1677ff" }}>加载中…</p>}

      {/* 结束摘要 */}
      {finish && (
        <Card title="复诊已结束 — 计费摘要" style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}>
          <p>
            诊次费用合计：<strong>¥{finish.gross_amount.toFixed(2)}</strong>
          </p>
          <div style={{ display: "grid", gap: 4 }}>
            {finish.splits.map((s) => (
              <div key={s.payee_type} style={{ display: "flex", gap: 12, fontSize: 13 }}>
                <span style={{ width: 80, color: "#8c8c8c" }}>{s.payee_type}</span>
                <span>¥{s.amount.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: 20 }}>
        {/* 候诊队列 */}
        <div>
          <h2 style={{ marginTop: 0 }}>候诊队列</h2>
          {consults.length === 0 && !loading && (
            <p style={{ color: "#8c8c8c" }}>暂无候诊记录</p>
          )}
          <div style={{ display: "grid", gap: 10 }}>
            {consults.map((c) => (
              <Card
                key={c.consult_no}
                title={`${c.consult_no}  —  患者 ${c.patient_id}`}
                onClick={() => selectConsult(c)}
                style={{
                  cursor: "pointer",
                  border: selected?.consult_no === c.consult_no ? "2px solid #1677ff" : undefined,
                }}
              >
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 13 }}>
                  <span style={{ color: STATUS_COLOR[c.status] ?? "#333" }}>
                    {STATUS_LABEL[c.status] ?? c.status}
                  </span>
                  <span>科室：{c.dept_code}</span>
                  {c.ai_triage && (
                    <span
                      style={{
                        background: c.ai_triage === "P1" ? "#fff1f0" : "#fff7e6",
                        padding: "1px 6px",
                        borderRadius: 4,
                        color: c.ai_triage === "P1" ? "#cf1322" : "#d46b08",
                      }}
                    >
                      AI分诊 {c.ai_triage}
                    </span>
                  )}
                  {c.chief_complaint && (
                    <span style={{ color: "#595959" }}>主诉：{c.chief_complaint}</span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 接诊详情 */}
        {selected && (
          <div>
            <h2 style={{ marginTop: 0 }}>
              {selected.consult_no}
              <button
                onClick={() => setSelected(null)}
                style={{ marginLeft: 12, fontSize: 12, cursor: "pointer" }}
              >
                关闭
              </button>
            </h2>

            <Card title="患者信息">
              <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
                <div>患者 ID：{selected.patient_id}</div>
                <div>科室：{selected.dept_code}</div>
                {selected.chief_complaint && <div>主诉：{selected.chief_complaint}</div>}
                {selected.ai_triage && <div>AI 分诊优先级：{selected.ai_triage}</div>}
                <div style={{ color: STATUS_COLOR[selected.status] }}>
                  状态：{STATUS_LABEL[selected.status]}
                </div>
              </div>
            </Card>

            {/* 接诊按钮 */}
            {selected.status === "waiting" && (
              <div style={{ marginTop: 12 }}>
                <Button onClick={() => handleAccept(selected.consult_no)}>开始接诊</Button>
              </div>
            )}

            {/* 开方区域 */}
            {selected.status === "in_progress" && (
              <Card title="AI 审方 · 开具处方" style={{ marginTop: 12 }}>
                <div style={{ display: "grid", gap: 10 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                      药品名称 *
                    </label>
                    <input
                      value={drugName}
                      onChange={(e) => setDrugName(e.target.value)}
                      placeholder="如：布洛芬缓释胶囊"
                      style={{
                        width: "100%",
                        padding: "6px 10px",
                        border: "1px solid #d9d9d9",
                        borderRadius: 6,
                        fontSize: 14,
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>
                      用法用量
                    </label>
                    <input
                      value={usage}
                      onChange={(e) => setUsage(e.target.value)}
                      placeholder="如：一日3次，每次1粒"
                      style={{
                        width: "100%",
                        padding: "6px 10px",
                        border: "1px solid #d9d9d9",
                        borderRadius: 6,
                        fontSize: 14,
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                  <Button onClick={handlePrescribe} disabled={!drugName.trim() || prescribing}>
                    {prescribing ? "AI 审方中…" : "提交处方"}
                  </Button>
                </div>

                {/* AI 审方结果 */}
                {rx && (
                  <div
                    style={{
                      marginTop: 12,
                      padding: "10px 14px",
                      background: rx.ai_review === "rejected" ? "#fff1f0" : rx.ai_review === "warn" ? "#fffbe6" : "#f6ffed",
                      borderRadius: 6,
                      border: `1px solid ${rx.ai_review === "rejected" ? "#ffa39e" : rx.ai_review === "warn" ? "#ffe58f" : "#b7eb8f"}`,
                    }}
                  >
                    <div style={{ fontWeight: 600, color: AI_REVIEW_COLOR[rx.ai_review] }}>
                      AI 审方：{AI_REVIEW_LABEL[rx.ai_review]} · {rx.drug_name}
                    </div>
                    {rx.review_note && (
                      <div style={{ fontSize: 13, color: "#595959", marginTop: 4 }}>{rx.review_note}</div>
                    )}
                  </div>
                )}

                {rx && rx.ai_review !== "rejected" && (
                  <div style={{ marginTop: 12 }}>
                    <Button onClick={handleFinish}>结束诊次 · 计费结算</Button>
                  </div>
                )}
              </Card>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
