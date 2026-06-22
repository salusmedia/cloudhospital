"use client";

import { Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type MdtSession,
  type MdtCreateIn,
  listMdt,
  getMdt,
  createMdt,
  submitOpinion,
  parseExperts,
} from "./mdt-api";

const STATUS_LABEL: Record<string, string> = {
  open: "进行中", done: "已出意见", closed: "已结束",
};

const STATUS_COLOR: Record<string, string> = {
  open: "#1677ff", done: "#389e0d", closed: "#8c8c8c",
};

export default function MdtView() {
  const [sessions, setSessions] = useState<MdtSession[]>([]);
  const [selected, setSelected] = useState<MdtSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  // 发起会诊表单
  const [showForm, setShowForm] = useState(false);
  const [topic, setTopic] = useState("");
  const [caseSummary, setCaseSummary] = useState("");
  const [refNo, setRefNo] = useState("");
  const [expertsText, setExpertsText] = useState("");
  const [creating, setCreating] = useState(false);

  // 提交意见
  const [opinion, setOpinion] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError(undefined);
    try {
      setSessions(await listMdt());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function selectSession(id: string) {
    setError(undefined);
    setOpinion("");
    try {
      setSelected(await getMdt(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载会诊详情失败");
    }
  }

  async function handleCreate() {
    if (!topic.trim()) return;
    setCreating(true);
    setError(undefined);
    try {
      const payload: MdtCreateIn = {
        topic: topic.trim(),
        case_summary: caseSummary || undefined,
        ref_no: refNo || undefined,
        experts: parseExperts(expertsText),
      };
      const created = await createMdt(payload);
      setShowForm(false);
      setTopic(""); setCaseSummary(""); setRefNo(""); setExpertsText("");
      await load();
      setSelected(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发起会诊失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleSubmitOpinion() {
    if (!selected || !opinion.trim()) return;
    setSubmitting(true);
    setError(undefined);
    try {
      await submitOpinion(selected.id, opinion.trim());
      setOpinion("");
      await selectSession(selected.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交意见失败");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "6px 10px", border: "1px solid #d9d9d9",
    borderRadius: 6, fontSize: 14, boxSizing: "border-box",
  };
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4,
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <Button onClick={load}>刷新</Button>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "取消" : "+ 发起会诊"}</Button>
      </div>

      {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}
      {loading && <p style={{ color: "#1677ff" }}>加载中…</p>}

      {/* 发起会诊 */}
      {showForm && (
        <Card title="发起 MDT 会诊" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <label style={labelStyle}>会诊主题 *</label>
              <input value={topic} onChange={(e) => setTopic(e.target.value)}
                placeholder="如：复杂冠心病多学科诊疗" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>病例摘要</label>
              <input value={caseSummary} onChange={(e) => setCaseSummary(e.target.value)}
                placeholder="主诉 / 现病史 / 关键检查（脱敏）" style={inputStyle} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12 }}>
              <div>
                <label style={labelStyle}>关联转诊单</label>
                <input value={refNo} onChange={(e) => setRefNo(e.target.value)}
                  placeholder="ZZ-… 可选" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>参与专家（每行：姓名,科室,机构）</label>
                <textarea value={expertsText} onChange={(e) => setExpertsText(e.target.value)}
                  placeholder={"张主任,心内科,温州市中心医院\n李医生,影像科"}
                  rows={3} style={{ ...inputStyle, fontFamily: "inherit", resize: "vertical" }} />
              </div>
            </div>
            <div>
              <Button onClick={handleCreate} disabled={!topic.trim() || creating}>
                {creating ? "提交中…" : "发起会诊"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1.3fr" : "1fr", gap: 20 }}>
        {/* 会诊列表 */}
        <div>
          <h2 style={{ marginTop: 0 }}>会诊列表（{sessions.length}）</h2>
          {sessions.length === 0 && !loading && <p style={{ color: "#8c8c8c" }}>暂无会诊</p>}
          <div style={{ display: "grid", gap: 10 }}>
            {sessions.map((s) => (
              <Card key={s.id} title={s.topic} onClick={() => selectSession(s.id)}
                style={{ cursor: "pointer", border: selected?.id === s.id ? "2px solid #1677ff" : undefined }}>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
                  <span style={{ color: STATUS_COLOR[s.status] ?? "#333" }}>
                    {STATUS_LABEL[s.status] ?? s.status}
                  </span>
                  <span style={{ color: "#8c8c8c" }}>专家 {s.experts.length} 人</span>
                  <span style={{ color: "#8c8c8c" }}>意见 {s.opinions.length} 条</span>
                  {s.ref_no && <span style={{ color: "#8c8c8c" }}>关联 {s.ref_no}</span>}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 会诊详情 */}
        {selected && (
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <h2 style={{ margin: 0 }}>{selected.topic}</h2>
              <button onClick={() => setSelected(null)}
                style={{ fontSize: 12, cursor: "pointer", color: "#8c8c8c", background: "none", border: "none" }}>
                关闭
              </button>
            </div>

            <Card title="病例信息">
              <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
                <div>
                  <span style={{ color: STATUS_COLOR[selected.status], fontWeight: 600 }}>
                    {STATUS_LABEL[selected.status] ?? selected.status}
                  </span>
                  {selected.ref_no && <span style={{ color: "#8c8c8c", marginLeft: 12 }}>关联转诊 {selected.ref_no}</span>}
                </div>
                {selected.case_summary && <div><span style={{ color: "#8c8c8c" }}>病例摘要：</span>{selected.case_summary}</div>}
              </div>
            </Card>

            <Card title={`参与专家（${selected.experts.length}）`}>
              {selected.experts.length === 0
                ? <p style={{ color: "#8c8c8c", fontSize: 13, margin: 0 }}>未指定专家</p>
                : (
                  <div style={{ display: "grid", gap: 6 }}>
                    {selected.experts.map((e) => (
                      <div key={e.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                        <span style={{ fontWeight: 600 }}>{e.name}</span>
                        {e.dept && <span style={{ color: "#8c8c8c" }}>{e.dept}</span>}
                        {e.org && <span style={{ color: "#8c8c8c" }}>· {e.org}</span>}
                        <span style={{
                          marginLeft: "auto", fontSize: 12,
                          color: e.confirmed ? "#389e0d" : "#d46b08",
                        }}>
                          {e.confirmed ? "✓ 已确认" : "待确认"}
                        </span>
                      </div>
                    ))}
                  </div>
                )
              }
            </Card>

            <Card title={`会诊意见（${selected.opinions.length}）`}>
              {selected.opinions.length === 0
                ? <p style={{ color: "#8c8c8c", fontSize: 13, margin: "0 0 12px" }}>暂无署名意见</p>
                : (
                  <div style={{ display: "grid", gap: 10, marginBottom: 12 }}>
                    {selected.opinions.map((o, i) => (
                      <div key={i} style={{ padding: "8px 12px", background: "#fafafa", borderRadius: 6, fontSize: 13 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", color: "#8c8c8c", fontSize: 12 }}>
                          <span>{o.name ?? "专家"}</span>
                          <span>{new Date(o.signed_at).toLocaleString("zh-CN")}</span>
                        </div>
                        <div style={{ marginTop: 4 }}>{o.opinion}</div>
                      </div>
                    ))}
                  </div>
                )
              }
              {/* 提交意见 */}
              <div style={{ display: "grid", gap: 8 }}>
                <textarea value={opinion} onChange={(e) => setOpinion(e.target.value)}
                  placeholder="填写署名会诊意见…" rows={2}
                  style={{ ...inputStyle, fontFamily: "inherit", resize: "vertical" }} />
                <div>
                  <Button onClick={handleSubmitOpinion} disabled={!opinion.trim() || submitting}>
                    {submitting ? "提交中…" : "提交署名意见"}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
