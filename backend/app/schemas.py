"""Pydantic response/request schemas.

Complex computed payloads (dashboard summary, ward risk, trends) are assembled
by the risk pipeline and declared with structured-but-nested dict fields;
entity payloads (wards, hospitals, ...) use strict typed schemas.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CityOut(ORMModel):
    id: int
    name: str
    state: str
    lat: float
    lon: float
    timezone: str


class WardSummaryOut(ORMModel):
    id: int
    city_id: int
    code: str
    name: str
    population: int
    centroid_lat: float
    centroid_lon: float


class WardOut(WardSummaryOut):
    elderly_pct: float
    outdoor_worker_density: float
    informal_housing_pct: float
    hospital_access_score: float
    population_density: float
    green_cover_pct: float
    chronic_disease_pct: float
    elevation_m: float
    area_km2: float
    geojson: dict[str, Any] | None = None


class HospitalOut(ORMModel):
    id: int
    name: str
    htype: str
    lat: float
    lon: float
    beds: int
    emergency_beds: int
    occupancy_pct: float
    has_icu: bool
    ors_units: int
    iv_fluids_units: int


class CoolingCentreOut(ORMModel):
    id: int
    name: str
    lat: float
    lon: float
    capacity: int
    current_occupancy: int
    water_stock_l: int
    ors_units: int
    opens: str
    closes: str


class WaterPointOut(ORMModel):
    id: int
    name: str
    lat: float
    lon: float
    wptype: str
    status: str


class HourOut(BaseModel):
    ts: str
    hour: str
    t: float
    rh: float
    wind: float
    solar: float
    cloud: float
    hi: float
    wbgt: float
    utci_proxy: float


class WeatherResponseOut(BaseModel):
    provider: str
    is_demo: bool
    fallback: bool
    scenario: str = ""
    current: dict[str, Any]
    daily: list[dict[str, Any]]
    hours: list[HourOut]


class WardRiskOut(BaseModel):
    ward_id: int
    ward_code: str
    ward_name: str
    date: str
    current: dict[str, Any]
    htsi: dict[str, Any]
    vulnerability: dict[str, Any]
    health: dict[str, Any]
    final: dict[str, Any]
    day: dict[str, Any]
    actions: list[dict[str, Any]] = []
    nearest: dict[str, Any] = {}


class CitySummaryOut(BaseModel):
    city: dict[str, Any]
    weather: dict[str, Any]
    current_conditions: dict[str, Any]
    risk: dict[str, Any]
    health: dict[str, Any]
    alerts: dict[str, Any]
    severe_window: dict[str, Any] | None
    action_plan: dict[str, Any] | None
    recommended_actions: list[dict[str, Any]]
    wards: list[dict[str, Any]]
    disclaimers: list[str]


class ActionOut(BaseModel):
    ward_id: int | None
    ward_code: str
    ward_name: str
    risk_level: str
    category: str
    title: str
    department: str
    priority: str
    reason: str
    status: str


class AlertOut(ORMModel):
    id: int
    ward_id: int
    ts: datetime
    severity: str
    title: str
    body_en: str
    body_kn: str
    channels: list[str]
    status: str
    sent_via: list[dict[str, Any]] = []
    delivered_at: datetime | None = None


class TriggerPlanIn(BaseModel):
    triggered_by: str = Field(default="Command Centre Officer", max_length=100)


class SettingsUpdateIn(BaseModel):
    """Partial settings update - only provided keys are changed."""
    risk_thresholds: list[int] | None = None
    htsi_weights: dict[str, float] | None = None
    vuln_weights: dict[str, float] | None = None
    final_weights: dict[str, float] | None = None
    escalate_vulnerability_threshold: float | None = None
    escalate_consecutive_days: int | None = None
    weather_provider: str | None = None
    demo_scenario: str | None = None
    city_id: int | None = None


class MessageOut(BaseModel):
    message: str
    detail: dict[str, Any] | None = None