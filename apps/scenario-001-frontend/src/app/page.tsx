"use client";

import { Button, Card } from "@hospital/ui";
import { useState } from "react";

import { listFollowups, type FollowupRecord } from "./followup-api";

// 样板页面：演示 用 @hospital/ui 组件 + 通过 @hospital/sdk 调后端。
export default function Page() {
  const [rows, setRows] = useState<FollowupRecord[]>([]);
  const [error, setError] = useState<string>();

  async function load() {
    setError(undefined);
    try {
      const page = await listFollowups();
      setRows(page.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  return (
    <main style={{ padding: 24, display: "grid", gap: 16, maxWidth: 720 }}>
      <h1>场景 001 · 在线随访</h1>
      <Button onClick={load}>加载随访记录</Button>
      {error && <p style={{ color: "#d4380d" }}>错误：{error}</p>}
      {rows.map((r) => (
        <Card key={r.id} title={`${r.patientName} · ${r.dept}`}>
          <p>随访日期：{r.visitDate}</p>
          <p>{r.note}</p>
        </Card>
      ))}
    </main>
  );
}
