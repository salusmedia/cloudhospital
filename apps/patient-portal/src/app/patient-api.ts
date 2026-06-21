import { createApiClient } from "@hospital/sdk";

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

// ---- 认证 ----
export interface LoginOut {
  token: string;
  name: string;
  patient_id: string | null;
  user_id: string;
}

export async function login(username: string, password: string): Promise<LoginOut> {
  return api.post<LoginOut>("/platform-auth/login", { username, password });
}

// ---- 复诊 (006) ----
export interface ConsultOut {
  consult_no: string;
  patient_id: string;
  dept_code: string;
  status: string;
  chief_complaint: string | null;
  ai_triage: string | null;
}

export const listMyConsults = () => api.get<ConsultOut[]>("/scenario-006/consults/mine");

export const createConsult = (chief_complaint: string, dept_code = "card") =>
  api.post<ConsultOut>("/scenario-006/consults", { chief_complaint, dept_code });

// ---- 转诊 (019) ----
export interface ReferralOut {
  ref_no: string;
  patient_id: string;
  dept_code: string;
  type: string;
  risk_level: string;
  status: string;
}

export interface NodeStatusOut {
  node: string;
  points: number;
  done: boolean;
}

export const listMyReferrals = () => api.get<ReferralOut[]>("/scenario-019/referrals/mine");

export const listReferralNodes = (ref_no: string) =>
  api.get<NodeStatusOut[]>(`/scenario-019/referrals/${ref_no}/nodes`);

// ---- 随访 (001) ----
export interface FollowupRecordOut {
  id: string;
  patient_id: string;
  plan_no: string | null;
  dept_code: string;
  visit_date: string;
  method: string;
  note: string | null;
  next_date: string | null;
  doctor_id: string | null;
}

export const listMyFollowups = () =>
  api.get<FollowupRecordOut[]>("/scenario-001/followups/mine");
