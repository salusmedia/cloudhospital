import { afterEach, describe, expect, it, vi } from "vitest";

import { createApiClient, SdkError } from "./index";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: `HTTP ${status}`,
    json: async () => body,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("createApiClient 响应契约", () => {
  it("直接返回后端裸载荷（不解包 .data）", async () => {
    // 后端登录返回顶层 { token, name }，无 { data } 信封
    vi.stubGlobal("fetch", mockFetch(200, { token: "t-123", name: "李医生" }));
    const api = createApiClient();
    const out = await api.post<{ token: string; name: string }>("/platform-auth/login", {});
    expect(out.token).toBe("t-123");
    expect(out.name).toBe("李医生");
  });

  it("裸数组原样返回", async () => {
    vi.stubGlobal("fetch", mockFetch(200, [{ id: "a" }, { id: "b" }]));
    const api = createApiClient();
    const out = await api.get<{ id: string }[]>("/scenario-019/referrals");
    expect(out).toHaveLength(2);
    expect(out[0].id).toBe("a");
  });

  it("错误时抛 SdkError，读 FastAPI 的 detail", async () => {
    vi.stubGlobal("fetch", mockFetch(403, { detail: "无权接收该转诊单" }));
    const api = createApiClient();
    await expect(api.post("/x", {})).rejects.toMatchObject({
      status: 403,
      message: "无权接收该转诊单",
    });
    await expect(api.post("/x", {})).rejects.toBeInstanceOf(SdkError);
  });

  it("错误时优先读网关的 message", async () => {
    vi.stubGlobal("fetch", mockFetch(401, { code: "NO_TOKEN", message: "缺少令牌" }));
    const api = createApiClient();
    await expect(api.get("/x")).rejects.toMatchObject({ status: 401, message: "缺少令牌" });
  });

  it("有 token 时注入 Authorization 头", async () => {
    const f = mockFetch(200, {});
    vi.stubGlobal("fetch", f);
    const api = createApiClient({ getToken: () => "tok-xyz" });
    await api.get("/me");
    const [, init] = f.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-xyz");
  });

  it("无 token 时不带 Authorization 头", async () => {
    const f = mockFetch(200, {});
    vi.stubGlobal("fetch", f);
    const api = createApiClient({ getToken: () => null });
    await api.get("/public");
    const [, init] = f.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});
