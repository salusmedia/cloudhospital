import { createApiClient } from "@hospital/sdk";
import type { Paginated } from "@hospital/shared-types";

// 本场景前端对后端的 typed 封装。组件只调这里，不裸用 fetch。
// 真实项目中 FollowupRecord 应来自 @hospital/shared-types 的 gen:types 生成类型。
export interface FollowupRecord {
  id: string;
  patientId: string;
  patientName: string; // 后端已脱敏
  dept: string;
  visitDate: string;
  note: string;
}

const api = createApiClient({
  // token 从统一登录态读取；此处示例从内存/存储取。
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

export function listFollowups(on?: string) {
  const q = on ? `?on=${encodeURIComponent(on)}` : "";
  return api.get<Paginated<FollowupRecord>>(`/scenario-001/followups${q}`);
}
