import { createApiClient } from "@hospital/sdk";

export interface ConsultOut {
  consult_no: string;
  patient_id: string;
  dept_code: string;
  status: "waiting" | "in_progress" | "finished";
  chief_complaint: string | null;
  ai_triage: string | null;
}

export interface RxOut {
  drug_name: string;
  usage: string | null;
  ai_review: "passed" | "warn" | "rejected";
  review_note: string | null;
}

export interface SplitOut {
  payee_type: string;
  amount: number;
}

export interface FinishOut {
  consult_no: string;
  status: string;
  gross_amount: number;
  splits: SplitOut[];
}

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-006";

export const listConsults = (status?: string) => {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return api.get<ConsultOut[]>(`${BASE}/consults${q}`);
};

export const acceptConsult = (no: string) =>
  api.post<ConsultOut>(`${BASE}/consults/${no}/accept`, {});

export const prescribe = (no: string, drug_name: string, usage?: string) =>
  api.post<RxOut>(`${BASE}/consults/${no}/prescribe`, { drug_name, usage });

export const finishConsult = (no: string) =>
  api.post<FinishOut>(`${BASE}/consults/${no}/finish`, {});
