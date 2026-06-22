import { createApiClient } from "@hospital/sdk";

// 本场景前端对后端的 typed 封装。组件只调这里，不裸用 fetch。
// 字段与后端响应保持一致（snake_case）。

export interface FollowupRecord {
  id: string;
  patient_id: string;
  plan_no: string | null;
  dept_code: string;
  visit_date: string;
  method: string; // phone / video / onsite
  note: string | null;
  next_date: string | null;
  doctor_id: string | null;
}

export interface FollowupPage {
  items: FollowupRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface FollowupPlan {
  id: string;
  plan_no: string;
  patient_id: string;
  dept_code: string;
  plan_type: string; // chronic / discharge / tumor
  interval_days: number;
  start_date: string;
  end_date: string | null;
  note: string | null;
}

export interface FollowupCreateIn {
  patient_id: string;
  dept_code?: string;
  visit_date: string;
  method?: string;
  note?: string;
  next_date?: string;
  plan_no?: string;
}

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-001";

/** 构造随访记录查询串（导出供单测）。 */
export function buildFollowupQuery(on?: string, dept?: string, page = 1): string {
  const params = new URLSearchParams();
  if (on) params.set("on", on);
  if (dept) params.set("dept", dept);
  if (page > 1) params.set("page", String(page));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const listFollowups = (on?: string, dept?: string, page = 1) =>
  api.get<FollowupPage>(`${BASE}/followups${buildFollowupQuery(on, dept, page)}`);

export const listPlans = () => api.get<FollowupPlan[]>(`${BASE}/plans`);

export const createFollowup = (payload: FollowupCreateIn) =>
  api.post<FollowupRecord>(`${BASE}/followups`, payload);
