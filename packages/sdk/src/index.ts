import type { ApiError, ApiResponse } from "@hospital/shared-types";

export interface ClientOptions {
  /** 网关基地址，默认走同源 /api（生产由 nginx 反代到网关） */
  baseUrl?: string;
  /** 返回当前会话 token；前端从统一登录态读取 */
  getToken?: () => string | null | undefined;
}

export class SdkError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiError,
  ) {
    super(body.message);
    this.name = "SdkError";
  }
}

/**
 * 创建统一 API 客户端。
 * - 自动注入鉴权头（鉴权由网关校验并下发用户身份）。
 * - 统一解析 ApiResponse / 抛出 SdkError。
 * 各场景应基于它封装自己的 typed 调用，不要在组件里裸用 fetch。
 */
export function createApiClient(opts: ClientOptions = {}) {
  const baseUrl = opts.baseUrl ?? "/api";

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = opts.getToken?.();
    const res = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });

    const json = (await res.json().catch(() => ({}))) as ApiResponse<T> & Partial<ApiError>;
    if (!res.ok) {
      throw new SdkError(res.status, {
        code: json.code ?? "UNKNOWN",
        message: json.message ?? res.statusText,
        traceId: json.traceId,
      });
    }
    return json.data;
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "POST", body: JSON.stringify(body) }),
    put: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
    del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
