"use client";

import { Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type FollowupRecord,
  type FollowupPlan,
  type FollowupCreateIn,
  listFollowups,
  listPlans,
  createFollowup,
} from "./followup-api";

const METHOD_LABEL: Record<string, string> = {
  phone: "电话随访", video: "视频随访", onsite: "面访",
};

const PLAN_TYPE_LABEL: Record<string, string> = {
  chronic: "慢病管理", discharge: "出院随访", tumor: "肿瘤随访",
};

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function Page() {
  const [plans, setPlans] = useState<FollowupPlan[]>([]);
  const [records, setRecords] = useState<FollowupRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [onDate, setOnDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  // 新增随访表单
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FollowupCreateIn>({
    patient_id: "",
    visit_date: todayStr(),
    method: "phone",
    note: "",
    next_date: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string>();

  async function load() {
    setLoading(true);
    setError(undefined);
    try {
      const [p, page] = await Promise.all([listPlans(), listFollowups(onDate || undefined)]);
      setPlans(p);
      setRecords(page.items);
      setTotal(page.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!form.patient_id.trim() || !form.visit_date) return;
    setSaving(true);
    setError(undefined);
    try {
      const payload: FollowupCreateIn = {
        patient_id: form.patient_id.trim(),
        visit_date: form.visit_date,
        method: form.method,
        note: form.note || undefined,
        next_date: form.next_date || undefined,
      };
      const rec = await createFollowup(payload);
      setSaved(`已新增随访记录（${rec.patient_id} · ${rec.visit_date}）`);
      setForm({ patient_id: "", visit_date: todayStr(), method: "phone", note: "", next_date: "" });
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "新增失败");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "6px 10px", border: "1px solid #d9d9d9",
    borderRadius: 6, fontSize: 14, boxSizing: "border-box",
  };
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4,
  };

  return (
    <main style={{ padding: 24, maxWidth: 1100 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>场景 001 · 在线随访</h1>
        <Button onClick={load}>刷新</Button>
        <Button onClick={() => { setShowForm(!showForm); setSaved(undefined); }}>
          {showForm ? "取消" : "+ 新增随访记录"}
        </Button>
      </div>

      {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}
      {saved && <p style={{ color: "#389e0d" }}>✓ {saved}</p>}
      {loading && <p style={{ color: "#1677ff" }}>加载中…</p>}

      {/* 新增表单 */}
      {showForm && (
        <Card title="新增随访记录" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div>
              <label style={labelStyle}>患者 ID *</label>
              <input
                value={form.patient_id}
                onChange={(e) => setForm({ ...form, patient_id: e.target.value })}
                placeholder="如：P-1001"
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>随访日期 *</label>
              <input
                type="date"
                value={form.visit_date}
                onChange={(e) => setForm({ ...form, visit_date: e.target.value })}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>随访方式</label>
              <select
                value={form.method}
                onChange={(e) => setForm({ ...form, method: e.target.value })}
                style={inputStyle}
              >
                <option value="phone">电话随访</option>
                <option value="video">视频随访</option>
                <option value="onsite">面访</option>
              </select>
            </div>
            <div style={{ gridColumn: "1 / 3" }}>
              <label style={labelStyle}>随访备注</label>
              <input
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                placeholder="如：血压平稳，继续原方案"
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>下次随访日期</label>
              <input
                type="date"
                value={form.next_date}
                onChange={(e) => setForm({ ...form, next_date: e.target.value })}
                style={inputStyle}
              />
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <Button onClick={handleCreate} disabled={!form.patient_id.trim() || !form.visit_date || saving}>
              {saving ? "保存中…" : "保存随访记录"}
            </Button>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20 }}>
        {/* 随访计划 */}
        <div>
          <h2 style={{ marginTop: 0 }}>随访计划（{plans.length}）</h2>
          {plans.length === 0 && !loading && <p style={{ color: "#8c8c8c" }}>暂无随访计划</p>}
          <div style={{ display: "grid", gap: 10 }}>
            {plans.map((p) => (
              <Card key={p.id} title={p.plan_no}>
                <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
                  <div>
                    <span style={{
                      background: "#e6f4ff", color: "#1677ff",
                      padding: "1px 8px", borderRadius: 10, marginRight: 8,
                    }}>
                      {PLAN_TYPE_LABEL[p.plan_type] ?? p.plan_type}
                    </span>
                    <span style={{ color: "#8c8c8c" }}>患者 {p.patient_id} · {p.dept_code}</span>
                  </div>
                  <div style={{ color: "#595959" }}>
                    每 {p.interval_days} 天随访 · 始于 {p.start_date}
                    {p.end_date ? ` 至 ${p.end_date}` : "（长期）"}
                  </div>
                  {p.note && <div style={{ color: "#8c8c8c" }}>{p.note}</div>}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 随访记录 */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>随访记录（{total}）</h2>
            <input
              type="date"
              value={onDate}
              onChange={(e) => setOnDate(e.target.value)}
              style={{ ...inputStyle, width: "auto" }}
            />
            <Button variant="secondary" onClick={load}>按日期筛选</Button>
            {onDate && (
              <button
                onClick={() => { setOnDate(""); }}
                style={{ fontSize: 12, color: "#8c8c8c", background: "none", border: "none", cursor: "pointer" }}
              >
                清除
              </button>
            )}
          </div>
          {records.length === 0 && !loading && <p style={{ color: "#8c8c8c" }}>暂无随访记录</p>}
          <div style={{ display: "grid", gap: 10 }}>
            {records.map((r) => (
              <Card key={r.id} title={`${r.visit_date} · ${METHOD_LABEL[r.method] ?? r.method}`}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 13 }}>
                  <div><span style={{ color: "#8c8c8c" }}>患者：</span>{r.patient_id}</div>
                  <div><span style={{ color: "#8c8c8c" }}>科室：</span>{r.dept_code}</div>
                  {r.plan_no && <div><span style={{ color: "#8c8c8c" }}>计划：</span>{r.plan_no}</div>}
                  {r.note && <div style={{ gridColumn: "1 / -1" }}><span style={{ color: "#8c8c8c" }}>备注：</span>{r.note}</div>}
                  {r.next_date && (
                    <div style={{ gridColumn: "1 / -1", color: "#1677ff" }}>
                      📅 下次随访：{r.next_date}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
