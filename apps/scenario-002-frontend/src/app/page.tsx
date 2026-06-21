"use client";

import { Button, Card } from "@hospital/ui";
import { useEffect, useState } from "react";

import {
  type BedOut,
  type BedMonitor,
  type HomebedDashboard,
  type TaskOut,
  getDashboard,
  listBeds,
  getBedMonitor,
  getBedTasks,
  reviewBed,
  dischargeBed,
  completTask,
} from "./homebed-api";

const STATUS_LABEL: Record<string, string> = {
  reviewing: "待审核",
  admitted: "在床",
  rejected: "已拒绝",
  discharged: "已出院",
};

const STATUS_COLOR: Record<string, string> = {
  reviewing: "#d46b08",
  admitted: "#389e0d",
  rejected: "#cf1322",
  discharged: "#8c8c8c",
};

export default function Page() {
  const [dashboard, setDashboard] = useState<HomebedDashboard | null>(null);
  const [beds, setBeds] = useState<BedOut[]>([]);
  const [selected, setSelected] = useState<BedOut | null>(null);
  const [monitor, setMonitor] = useState<BedMonitor | null>(null);
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  async function loadAll() {
    setLoading(true);
    setError(undefined);
    try {
      const [dash, bedList] = await Promise.all([getDashboard(), listBeds()]);
      setDashboard(dash);
      setBeds(bedList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function selectBed(bed: BedOut) {
    setSelected(bed);
    setMonitor(null);
    setTasks([]);
    try {
      const [mon, taskList] = await Promise.all([
        getBedMonitor(bed.bed_no),
        getBedTasks(bed.bed_no),
      ]);
      setMonitor(mon);
      setTasks(taskList);
    } catch {
      // 非关键，忽略
    }
  }

  async function handleReview(no: string, approved: boolean) {
    await reviewBed(no, approved);
    await loadAll();
    setSelected(null);
  }

  async function handleDischarge(no: string) {
    await dischargeBed(no);
    await loadAll();
    setSelected(null);
  }

  async function handleTaskDone(taskId: string) {
    await completTask(taskId);
    if (selected) {
      const updated = await getBedTasks(selected.bed_no);
      setTasks(updated);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <main style={{ padding: 24, display: "grid", gap: 20, maxWidth: 1100 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <h1 style={{ margin: 0 }}>场景 002 · 家庭病床管理</h1>
        <Button onClick={loadAll}>刷新</Button>
      </div>

      {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}
      {loading && <p style={{ color: "#1677ff" }}>加载中…</p>}

      {/* 看板指标 */}
      {dashboard && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            { label: "病床总数", value: dashboard.total_beds },
            { label: "在床患者", value: dashboard.active_beds },
            { label: "待处理任务", value: dashboard.pending_tasks },
            { label: "平均住院天数", value: dashboard.avg_stay_days.toFixed(1) },
            { label: "床位占用率", value: `${(dashboard.occupancy_rate * 100).toFixed(0)}%` },
            { label: "床位周转率", value: dashboard.bed_turnover_rate.toFixed(2) },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                background: "#f5f5f5",
                borderRadius: 8,
                padding: "12px 16px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 24, fontWeight: 700, color: "#1677ff" }}>{item.value}</div>
              <div style={{ fontSize: 12, color: "#8c8c8c" }}>{item.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: 20 }}>
        {/* 病床列表 */}
        <div>
          <h2 style={{ marginTop: 0 }}>病床列表</h2>
          {beds.length === 0 && !loading && <p style={{ color: "#8c8c8c" }}>暂无病床记录</p>}
          <div style={{ display: "grid", gap: 10 }}>
            {beds.map((b) => (
              <Card
                key={b.bed_no}
                title={`${b.bed_no}  —  患者 ${b.patient_id}`}
                onClick={() => selectBed(b)}
                style={{
                  cursor: "pointer",
                  border: selected?.bed_no === b.bed_no ? "2px solid #1677ff" : undefined,
                }}
              >
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 13 }}>
                  <span style={{ color: STATUS_COLOR[b.status] ?? "#333" }}>
                    状态：{STATUS_LABEL[b.status] ?? b.status}
                  </span>
                  {b.care_level && <span>护理：{b.care_level}</span>}
                  {b.admit_date && <span>建床：{b.admit_date}</span>}
                  {b.attending_doctor && <span>责任医：{b.attending_doctor}</span>}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 病床详情 */}
        {selected && (
          <div>
            <h2 style={{ marginTop: 0 }}>
              {selected.bed_no} 详情
              <button
                onClick={() => setSelected(null)}
                style={{ marginLeft: 12, fontSize: 12, cursor: "pointer" }}
              >
                关闭
              </button>
            </h2>

            {/* 操作按钮 */}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
              {selected.status === "reviewing" && (
                <>
                  <Button onClick={() => handleReview(selected.bed_no, true)}>通过准入</Button>
                  <Button onClick={() => handleReview(selected.bed_no, false)}>拒绝准入</Button>
                </>
              )}
              {selected.status === "admitted" && (
                <Button onClick={() => handleDischarge(selected.bed_no)}>办理出院</Button>
              )}
            </div>

            {/* 体征监测 */}
            {monitor && (
              <Card title={`体征监测${monitor.alert_count > 0 ? ` ⚠ ${monitor.alert_count} 项异常` : ""}`}>
                {monitor.latest.length === 0 && (
                  <p style={{ color: "#8c8c8c", margin: 0 }}>暂无体征数据</p>
                )}
                <div style={{ display: "grid", gap: 6 }}>
                  {monitor.latest.map((v) => (
                    <div
                      key={v.metric}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        color: v.abnormal_flag ? "#d4380d" : undefined,
                        fontSize: 13,
                      }}
                    >
                      <span>{v.metric}</span>
                      <span>
                        {v.value_text} {v.unit}
                        {v.abnormal_flag && " ⚠"}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* 护理任务 */}
            {tasks.length > 0 && (
              <Card title="护理任务" style={{ marginTop: 12 }}>
                <div style={{ display: "grid", gap: 8 }}>
                  {tasks.map((t) => (
                    <div
                      key={t.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        fontSize: 13,
                      }}
                    >
                      <span style={{ color: t.done ? "#8c8c8c" : "#333", flex: 1 }}>
                        {t.task_type}
                        {t.note && ` · ${t.note}`}
                      </span>
                      <span style={{ color: "#8c8c8c", fontSize: 11 }}>
                        {new Date(t.scheduled_at).toLocaleString("zh-CN")}
                      </span>
                      {!t.done && (
                        <Button onClick={() => handleTaskDone(t.id)}>完成</Button>
                      )}
                      {t.done && <span style={{ color: "#52c41a" }}>✓</span>}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
