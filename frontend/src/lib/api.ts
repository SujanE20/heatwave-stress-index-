import type {
  Alert, CoverageGap, CoolingCentre, DashboardSummary, DataSources, Hospital,
  HyperlocalMap, ModelMeta, SettingsPayload, Trends, WardForecast, WardLite, WardRisk, WaterPoint,
} from "./types";

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, `Cannot reach backend at ${API_URL}. Start it with Docker Compose or \`uvicorn app.main:app\`.`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<any>("/health"),
  dashboard: () => request<DashboardSummary>("/api/v1/dashboard/summary"),
  wards: (includeGeometry = false) =>
    request<WardLite[]>(`/api/v1/wards?include_geometry=${includeGeometry}`),
  hyperlocal: () => request<HyperlocalMap>("/api/v1/map/hyperlocal"),
  ward: (id: number | string) => request<WardRisk>(`/api/v1/wards/${id}`),
  wardForecast: (id: number | string) => request<WardForecast>(`/api/v1/wards/${id}/forecast`),
  weatherCurrent: () => request<any>("/api/v1/weather/current"),
  trends: () => request<Trends>("/api/v1/analytics/trends"),
  alerts: () => request<Alert[]>("/api/v1/alerts"),
  generateAlerts: (minLevel = "orange", channels = ["dashboard", "sms", "whatsapp", "webhook"]) =>
    request<{ generated: number; alerts: any[]; note: string }>("/api/v1/alerts/generate", {
      method: "POST",
      body: JSON.stringify({ min_level: minLevel, channels }),
    }),
  sendAlerts: (alertIds: number[], channels = ["sms", "whatsapp"]) =>
    request<{ sent: number; alerts: any[]; note: string }>("/api/v1/alerts/send", {
      method: "POST",
      body: JSON.stringify({ alert_ids: alertIds, channels }),
    }),
  triggerHeatActionPlan: (triggeredBy = "Command Centre Officer") =>
    request<{ message: string; detail: { plan_id: number; summary: string } }>(
      "/api/v1/actions/trigger-heat-action-plan",
      { method: "POST", body: JSON.stringify({ triggered_by: triggeredBy }) }
    ),
  hospitals: () => request<Hospital[]>("/api/v1/resources/hospitals"),
  coolingCentres: () => request<CoolingCentre[]>("/api/v1/resources/cooling-centres"),
  waterPoints: () => request<WaterPoint[]>("/api/v1/resources/water-points"),
  coverage: () => request<CoverageGap[]>("/api/v1/resources/ward-coverage"),
  settings: () => request<SettingsPayload>("/api/v1/settings"),
  updateSettings: (patch: Record<string, any>) =>
    request<{ message: string; settings: any }>("/api/v1/settings", {
      method: "POST",
      body: JSON.stringify(patch),
    }),
  retrainModel: () => request<{ message: string; metadata: ModelMeta }>("/api/v1/admin/retrain-model", {
    method: "POST",
  }),
  modelMeta: () => request<ModelMeta>("/api/v1/admin/model"),
  dataSources: () => request<DataSources>("/api/v1/admin/data-sources"),
  sampleCsv: () => request<{ filename: string; content: string; columns: string[] }>("/api/v1/admin/sample-csv"),
};