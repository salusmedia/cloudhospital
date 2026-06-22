import { createApiClient } from "@hospital/sdk";

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-019/admin";

// ---- 认证 ----
export interface LoginOut {
  token: string;
  name: string;
  user_id: string;
  roles: string[];
}

export async function login(username: string, password: string): Promise<LoginOut> {
  return api.post<LoginOut>("/platform-auth/login", { username, password });
}

// ---- 监管看板 ----
export interface Kpi {
  total: number;
  up: number;
  down: number;
  flat: number;
  emergency: number;
  received_rate: number;
  mutual_recognition_rate: number;
}

export interface OrgRank {
  org_id: string;
  org_name: string | null;
  inbound: number;
}

export interface Dashboard {
  kpi: Kpi;
  type_distribution: Record<string, number>;
  org_ranking: OrgRank[];
}

export const getDashboard = () => api.get<Dashboard>(`${BASE}/dashboard`);

// ---- 绩效分账 ----
export interface Measure {
  name: string;
  qty: number;
  unit: number;
  subtotal: number;
}

export interface OrgSettlement {
  org_id: string;
  period: string;
  service_amount: number;
  quality_bonus: number;
  actual_alloc: number;
}

export interface SettlementOut {
  measures: Measure[];
  org_settlements: OrgSettlement[];
}

export const getSettlements = () => api.get<SettlementOut>(`${BASE}/settlements`);

// ---- 规则配置 ----
export interface RuleLayer { level: string; desc: string }
export interface TimeLimit { scene: string; limit: string; warn: string }
export interface MrCatalog {
  category: string;
  item_name: string;
  valid_days: number;
  recognize_scope: string;
  status: string;
}
export interface RulesOut {
  risk_layers: RuleLayer[];
  time_limits: TimeLimit[];
  mutual_recognition: MrCatalog[];
}

export const getRules = () => api.get<RulesOut>(`${BASE}/rules`);

// ---- 异常预警 ----
export interface AlertOut {
  id: string;
  ref_no: string | null;
  level: string;
  category: string;
  title: string;
  detail: string | null;
  status: string;
}

export const getAlerts = () => api.get<AlertOut[]>(`${BASE}/alerts`);

export const handleAlert = (id: string) =>
  api.post<{ id: string; status: string }>(`${BASE}/alerts/${id}/handle`, {});
