// Types mirroring the HEATSHIELD backend API payloads (snake_case preserved).

export type RiskKey = "green" | "yellow" | "orange" | "red" | "maroon";

export interface RiskLevel {
  key: RiskKey;
  label: string;
  score: number;
}

export interface WardLite {
  id: number;
  city_id: number;
  code: string;
  name: string;
  population: number;
  elderly_pct: number;
  outdoor_worker_density: number;
  informal_housing_pct: number;
  hospital_access_score: number;
  population_density: number;
  green_cover_pct: number;
  chronic_disease_pct: number;
  elevation_m: number;
  area_km2: number;
  centroid_lat: number;
  centroid_lon: number;
  risk?: FinalRisk;
  geojson?: any;
}

export interface CurrentConditions {
  t: number;
  rh: number;
  wind: number;
  wind_dir: number;
  solar: number;
  cloud: number;
  precip_prob: number;
  hi: number;
  wbgt: number;
  utci_proxy: number;
  apparent: number;
  htsi?: number;
  htsi_components?: Record<string, number>;
  observed_at?: string;
}

export interface DashboardSummary {
  city: { id: number; name: string; state: string; lat: number; lon: number };
  weather: { provider: string; scenario: string; is_demo: boolean; fallback: boolean };
  current_conditions: CurrentConditions;
  risk: {
    city_level: RiskKey;
    city_label: string;
    ward_counts: Record<RiskKey, number>;
    high_risk_wards: number;
    people_exposed: number;
    vulnerable_exposed: number;
    high_risk_ward_names: string[];
  };
  health: { demand_increase_pct: number; demand_range_pct: string; label: string };
  alerts: { active: number };
  severe_window: { date: string; start: string; end: string; peak_wbgt: number } | null;
  action_plan: { id: number; status: string; triggered_at: string; summary: string } | null;
  recommended_actions: { title: string; department: string; priority: string }[];
  wards: {
    id: number; code: string; name: string; level: RiskKey; label: string;
    score: number; htsi: number; vulnerability: number; population: number;
    centroid_lat: number; centroid_lon: number;
  }[];
  disclaimers: string[];
}

export interface WardRisk {
  ward_id: number;
  ward_code: string;
  ward_name: string;
  date: string;
  current: CurrentConditions;
  htsi: { score: number; components: Record<string, number> };
  vulnerability: {
    score: number;
    components: Record<string, number>;
    contributions: Record<string, number>;
    weights: Record<string, number>;
    labels: Record<string, string>;
  };
  health: {
    score: number;
    hospitalization_risk: string;
    mortality_risk_band: string;
    demand_increase_pct: {
      predicted: number; range_pct: string; min: number; max: number;
      source: string; label: string;
    };
    confidence: string;
    drivers: { name: string; contribution_pct: number }[];
    inputs: Record<string, number>;
    safety_notes: string[];
  };
  final: FinalRisk;
  day: Record<string, any>;
  actions: Action[];
  nearest: {
    hospital: { name: string; distance_km: number };
    cooling_centre: { name: string; distance_km: number };
    water_point: { name: string; distance_km: number };
  };
}

export interface FinalRisk {
  score: number;
  base_score: number;
  level: RiskKey;
  label: string;
  base_level: RiskKey;
  base_label: string;
  escalations: string[];
  explanation: string;
  weights: Record<string, number>;
}

export interface Action {
  ward_id: number | null;
  ward_code: string;
  ward_name: string;
  risk_level: RiskKey;
  category: string;
  title: string;
  department: string;
  priority: "Immediate" | "Today" | "Monitor";
  reason: string;
  status: "Pending" | "In Progress" | "Completed";
}

export interface Alert {
  id: number;
  ward_id: number;
  ts: string;
  severity: string;
  title: string;
  body_en: string;
  body_kn: string;
  sms: string;
  whatsapp: string;
  channels: string[];
  status: string;
  sent_via: { channel: string; status: string; delivered_at: string }[];
  delivered_at: string | null;
}

export interface WardForecast {
  ward_id: number;
  ward_code: string;
  ward_name: string;
  daily: {
    date: string; tmax: number; tmin: number; rh: number; wind: number;
    hi_max: number; wbgt_max: number; utci_max: number;
    exposure_hours: number; consecutive_days: number;
    htsi: number; risk_level: RiskKey; risk_label: string;
    health_demand: { predicted: number; range_pct: string };
    mortality_band: string; confidence: string;
  }[];
  hourly: {
    ts: string; hour: number; t: number; rh: number; wind: number;
    solar: number; hi: number; wbgt: number; utci_proxy: number;
  }[];
}

export interface Trends {
  forecast: {
    date: string; tmax: number; tmin: number; hi_max: number; wbgt_max: number;
    utci_max: number; htsi: number; risk_level: RiskKey; risk_label: string;
  }[];
  hourly: {
    ts: string; hour: string; t: number; apparent: number; hi: number;
    wbgt: number; utci_proxy: number;
  }[];
  ward_comparison: {
    id: number; code: string; name: string; population: number;
    risk_level: RiskKey; risk_label: string; risk_score: number;
    htsi: number; vulnerability: number; health_score: number;
    wbgt_max: number; consecutive_days: number;
  }[];
  scatter: { ward: string; x: number; y: number; risk: RiskKey }[];
  hospital_load_history: {
    date: string; load_increase_pct: number; heat_admissions: number;
    wbgt_max: number; tmax: number;
  }[];
  alert_history: { id: number; ts: string; ward_id: number; severity: string; title: string; status: string; channels: string[] }[];
  intervention_effectiveness: {
    note: string;
    series: { day: string; excess_health_demand_pct: number }[];
    estimated_effect: string;
  };
  weather: { provider: string; is_demo: boolean; fallback: boolean };
}

export interface Hospital {
  id: number; name: string; type: string; lat: number; lon: number;
  beds: number; emergency_beds: number; available_emergency_beds: number;
  occupancy_pct: number; has_icu: boolean; ors_units: number; iv_fluids_units: number;
  expected_heat_admissions_3_5d: number; note: string;
}

export interface CoolingCentre {
  id: number; name: string; lat: number; lon: number; capacity: number;
  current_occupancy: number; occupancy_pct: number; water_stock_l: number;
  ors_units: number; opens: string; closes: string; hours_remaining_today: string; note: string;
}

export interface WaterPoint {
  id: number; name: string; lat: number; lon: number; type: string; status: string;
}

export interface CoverageGap {
  ward_id: number; ward_code: string; ward_name: string;
  vulnerable_exposed: number; risk_level: RiskKey; risk_label: string;
  nearest_cooling_centre: string; distance_km: number; recommendation: string;
}

export interface HyperlocalExposure {
  score: number;
  components: Record<string, number>;
  contributions: Record<string, number>;
  weights: Record<string, number>;
  labels: Record<string, string>;
  kind: string;
  nearest: {
    cooling_centre: { name: string; distance_km: number };
    water_point: { name: string; distance_km: number };
  };
}

export interface HyperlocalZone {
  id: string;
  zone_index: number;
  role: "core" | "outer";
  ward_id: number;
  ward_code: string;
  ward_name: string;
  name: string;
  kind: string;
  level: RiskKey;
  label: string;
  score: number;
  base_score: number;
  escalations: string[];
  exposure: HyperlocalExposure;
  htsi: number;
  ward_level: RiskKey;
  ward_label: string;
  ward_score: number;
  population: number;
  population_share: number;
  centroid_lat: number;
  centroid_lon: number;
  explanation: string;
  geojson: any;
}

export interface HyperlocalWardOutline {
  id: number; code: string; name: string; level: RiskKey; label: string;
  score: number; htsi: number; vulnerability: number; population: number;
  centroid_lat: number; centroid_lon: number; geojson: any;
}

export interface HyperlocalMap {
  city: { id: number; name: string; state: string; lat: number; lon: number };
  weather: { provider: string; scenario: string; is_demo: boolean; fallback: boolean };
  shared_heat_note: string;
  generated_note: string;
  wards: HyperlocalWardOutline[];
  zones: HyperlocalZone[];
}

export interface SettingsPayload {
  settings: {
    risk_thresholds: number[];
    htsi_weights: Record<string, number>;
    vuln_weights: Record<string, number>;
    final_weights: Record<string, number>;
    escalate_vulnerability_threshold: number;
    escalate_consecutive_days: number;
    weather_provider: string;
    demo_scenario: string;
    city_id: number;
  };
  methodology: Record<string, any>;
  defaults: Record<string, any>;
  scenarios: Record<string, string>;
}

export interface ModelMeta {
  trained_at: string;
  model_type: string;
  n_samples: number;
  metrics: Record<string, number>;
  feature_importance: Record<string, number>;
  fallback_used: boolean;
}

export interface DataSources {
  weather_provider: string;
  is_demo: boolean;
  scenario: string;
  counts: Record<string, number>;
  model: ModelMeta | null;
  postgis: string;
  health_data_policy: string;
}