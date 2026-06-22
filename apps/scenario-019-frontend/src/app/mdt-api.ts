import { createApiClient } from "@hospital/sdk";

export interface MdtExpert {
  id: string;
  name: string;
  dept: string | null;
  org: string | null;
  role: string | null;
  user_id: string | null;
  confirmed: boolean;
}

export interface MdtOpinion {
  name: string | null;
  opinion: string;
  signed_at: string;
}

export interface MdtSession {
  id: string;
  topic: string;
  case_summary: string | null;
  ref_no: string | null;
  status: string;
  host_user: string | null;
  experts: MdtExpert[];
  opinions: MdtOpinion[];
}

export interface ExpertIn {
  name: string;
  dept?: string;
  org?: string;
  role?: string;
}

export interface MdtCreateIn {
  topic: string;
  case_summary?: string;
  ref_no?: string;
  experts?: ExpertIn[];
}

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-019/mdt";

/** 把"姓名,科室,机构"多行文本解析为专家数组（导出供单测）。 */
export function parseExperts(text: string): ExpertIn[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, dept, org] = line.split(/[,，]/).map((s) => s.trim());
      const e: ExpertIn = { name };
      if (dept) e.dept = dept;
      if (org) e.org = org;
      return e;
    })
    .filter((e) => e.name);
}

export const listMdt = () => api.get<MdtSession[]>(BASE);

export const getMdt = (id: string) => api.get<MdtSession>(`${BASE}/${id}`);

export const createMdt = (payload: MdtCreateIn) => api.post<MdtSession>(BASE, payload);

export const submitOpinion = (id: string, opinion: string) =>
  api.post<MdtOpinion>(`${BASE}/${id}/opinion`, { opinion });
