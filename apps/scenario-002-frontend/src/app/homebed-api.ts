import { createApiClient } from "@hospital/sdk";

export interface BedOut {
  bed_no: string;
  patient_id: string;
  status: "reviewing" | "admitted" | "rejected" | "discharged";
  care_level: string | null;
  attending_doctor: string | null;
  admit_date: string | null;
}

export interface VitalOut {
  metric: string;
  value_text: string | null;
  unit: string | null;
  measured_at: string;
  abnormal_flag: boolean;
}

export interface BedMonitor {
  bed_no: string;
  patient_id: string;
  latest: VitalOut[];
  alert_count: number;
}

export interface TaskOut {
  id: string;
  bed_no: string;
  task_type: string;
  scheduled_at: string;
  done: boolean;
  done_at: string | null;
  done_by: string | null;
  note: string | null;
}

export interface HomebedDashboard {
  total_beds: number;
  active_beds: number;
  pending_tasks: number;
  avg_stay_days: number;
  occupancy_rate: number;
  bed_turnover_rate: number;
}

const api = createApiClient({
  getToken: () => (typeof window !== "undefined" ? window.localStorage.getItem("token") : null),
});

const BASE = "/scenario-002";

export const listBeds = (status?: string) => {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return api.get<BedOut[]>(`${BASE}/beds${q}`);
};

export const getDashboard = () => api.get<HomebedDashboard>(`${BASE}/dashboard`);

export const getBedMonitor = (no: string) => api.get<BedMonitor>(`${BASE}/beds/${no}/monitor`);

export const getBedTasks = (no: string) => api.get<TaskOut[]>(`${BASE}/beds/${no}/tasks`);

export const createBed = (body: { patient_id: string; care_level?: string; dept_code?: string }) =>
  api.post<BedOut>(`${BASE}/beds`, body);

export const reviewBed = (no: string, approved: boolean, note?: string) =>
  api.post<BedOut>(`${BASE}/beds/${no}/review`, { approved, note });

export const completTask = (taskId: string, note?: string) =>
  api.post<TaskOut>(`${BASE}/tasks/${taskId}/done`, { note });

export const dischargeBed = (no: string) =>
  api.post<{ bed_no: string; status: string; gross_amount: number }>(`${BASE}/beds/${no}/discharge`, {});
