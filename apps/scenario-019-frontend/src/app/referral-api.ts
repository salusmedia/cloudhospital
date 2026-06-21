import { createApiClient } from "@hospital/sdk";

export interface ReferralOut {
  ref_no: string;
  patient_id: string;
  dept_code: string;
  type: string;
  risk_level: string;
  status: string;
}

export interface SplitOut {
  payee_type: string;
  payee_id: string;
  amount: number;
}

export interface ReceiveOut {
  ref_no: string;
  status: string;
  gross_amount: number;
  splits: SplitOut[];
}

export interface NodeStatusOut {
  node: string;
  points: number;
  done: boolean;
}

export interface NodeCompleteOut {
  ref_no: string;
  node: string;
  points: number;
  earned: number;
  account_points: number;
  account_balance: number;
}

export interface LedgerItem {
  node: string;
  points: number;
  earned: number;
}

export interface AccountOut {
  user_id: string;
  points: number;
  balance: number;
  ledger: LedgerItem[];
}

export interface ReferralCreateIn {
  patient_id: string;
  type?: string;
  risk_level?: string;
  dept_code?: string;
  source_org?: string;
  target_org?: string;
}

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-019";

export const listReferrals = () => api.get<ReferralOut[]>(`${BASE}/referrals`);

export const createReferral = (payload: ReferralCreateIn) =>
  api.post<ReferralOut>(`${BASE}/referrals`, payload);

export const receiveReferral = (ref_no: string) =>
  api.post<ReceiveOut>(`${BASE}/referrals/${ref_no}/receive`, {});

export const listNodes = (ref_no: string) =>
  api.get<NodeStatusOut[]>(`${BASE}/referrals/${ref_no}/nodes`);

export const completeNode = (ref_no: string, node: string) =>
  api.post<NodeCompleteOut>(`${BASE}/referrals/${ref_no}/nodes/${node}/complete`, {});

export const getCreditAccount = () => api.get<AccountOut>(`${BASE}/credit/account`);
