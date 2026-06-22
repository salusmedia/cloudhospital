"use client";

import { useEffect, useState, type ReactNode } from "react";

const TOKEN_KEY = "token";

/** 解析登录响应，取出 token（导出供单测；后端裸返回顶层 token）。 */
export function extractToken(body: unknown): string | null {
  if (body && typeof body === "object" && "token" in body) {
    const t = (body as { token?: unknown }).token;
    if (typeof t === "string" && t) return t;
  }
  return null;
}

async function doLogin(username: string, password: string): Promise<string> {
  const res = await fetch("/api/platform-auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (body as { detail?: string; message?: string }).detail
      ?? (body as { message?: string }).message
      ?? "登录失败";
    throw new Error(msg);
  }
  const token = extractToken(body);
  if (!token) throw new Error("登录响应缺少令牌");
  return token;
}

/**
 * 统一登录守卫：未登录显示登录框，登录后渲染 children。
 * token 存 localStorage（与 @hospital/sdk 的 getToken 约定一致）。
 */
export function AuthGate({ title, children }: { title?: string; children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setAuthed(typeof window !== "undefined" && !!window.localStorage.getItem(TOKEN_KEY));
    setReady(true);
  }, []);

  async function submit() {
    if (!username.trim() || !password) return;
    setBusy(true);
    setError(undefined);
    try {
      const token = await doLogin(username.trim(), password);
      window.localStorage.setItem(TOKEN_KEY, token);
      setAuthed(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return null;

  if (authed) {
    return (
      <>
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "8px 16px 0" }}>
          <button
            onClick={() => { window.localStorage.removeItem(TOKEN_KEY); setAuthed(false); }}
            style={{ fontSize: 12, color: "#8c8c8c", background: "none", border: "1px solid #eee", borderRadius: 4, padding: "4px 10px", cursor: "pointer" }}
          >
            退出登录
          </button>
        </div>
        {children}
      </>
    );
  }

  const input: React.CSSProperties = {
    width: "100%", padding: "8px 12px", border: "1px solid #d9d9d9",
    borderRadius: 6, fontSize: 14, boxSizing: "border-box",
  };

  return (
    <main style={{ minHeight: "70vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 340, padding: 32, border: "1px solid #eee", borderRadius: 10 }}>
        <h2 style={{ margin: "0 0 4px", textAlign: "center" }}>{title ?? "医护工作站登录"}</h2>
        <p style={{ color: "#8c8c8c", fontSize: 13, textAlign: "center", margin: "0 0 20px" }}>
          AI 云医院 · 真实接口 · 真实数据库
        </p>
        {error && <p style={{ color: "#cf1322", fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>账号</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} style={input} placeholder="如 doctor_card" />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>密码</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()} style={input} placeholder="123456" />
          </div>
          <button onClick={submit} disabled={busy || !username.trim() || !password}
            style={{ padding: 10, background: "#1677ff", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
            {busy ? "登录中…" : "登录"}
          </button>
        </div>
      </div>
    </main>
  );
}
