"""SQLAlchemy ORM models for HEATSHIELD INDIA."""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(50), default="Karnataka")
    lat: Mapped[float]
    lon: Mapped[float]
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")


class Ward(Base):
    """Ward-level demographics. Geometry stored as GeoJSON (JSONB on Postgres).
    PostGIS is provisioned in Docker for spatial queries; a migration to native
    geometry columns is documented in docs/architecture.md."""

    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    population: Mapped[int]
    elderly_pct: Mapped[float]              # % of population aged 60+
    outdoor_worker_density: Mapped[float]   # outdoor workers per km2
    informal_housing_pct: Mapped[float]     # informal-settlement proxy %
    hospital_access_score: Mapped[float]    # 0-100, higher = better access
    population_density: Mapped[float]       # people per km2
    green_cover_pct: Mapped[float]          # tree/green cover %
    chronic_disease_pct: Mapped[float]      # chronic-disease prevalence proxy %
    elevation_m: Mapped[float]
    area_km2: Mapped[float]
    centroid_lat: Mapped[float]
    centroid_lon: Mapped[float]
    geojson: Mapped[dict] = mapped_column(JSON)


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    name: Mapped[str] = mapped_column(String(150))
    htype: Mapped[str] = mapped_column(String(50))  # District / Taluka / Private / Primary Health Centre
    lat: Mapped[float]
    lon: Mapped[float]
    beds: Mapped[int]
    emergency_beds: Mapped[int]
    occupancy_pct: Mapped[float]
    has_icu: Mapped[bool] = mapped_column(Boolean, default=True)
    ors_units: Mapped[int] = mapped_column(default=0)
    iv_fluids_units: Mapped[int] = mapped_column(default=0)


class CoolingCentre(Base):
    __tablename__ = "cooling_centres"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    name: Mapped[str] = mapped_column(String(150))
    lat: Mapped[float]
    lon: Mapped[float]
    capacity: Mapped[int]
    current_occupancy: Mapped[int] = mapped_column(default=0)
    water_stock_l: Mapped[int] = mapped_column(default=0)
    ors_units: Mapped[int] = mapped_column(default=0)
    opens: Mapped[str] = mapped_column(String(10), default="10:00")
    closes: Mapped[str] = mapped_column(String(10), default="18:00")


class WaterPoint(Base):
    __tablename__ = "water_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    name: Mapped[str] = mapped_column(String(150))
    lat: Mapped[float]
    lon: Mapped[float]
    wptype: Mapped[str] = mapped_column(String(40))  # Standpost / Tanker / Community tap
    status: Mapped[str] = mapped_column(String(20), default="Operational")


class WeatherHour(Base):
    """Hourly weather (raw provider variables + derived thermal indices)."""

    __tablename__ = "weather_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    provider: Mapped[str] = mapped_column(String(20), default="demo")
    scenario: Mapped[str] = mapped_column(String(40), default="")
    t: Mapped[float]                 # temperature_2m (°C)
    rh: Mapped[float]                # relative_humidity_2m (%)
    wind: Mapped[float]              # wind_speed_10m (m/s)
    wind_dir: Mapped[float] = mapped_column(default=0)
    solar: Mapped[float]             # shortwave_radiation (W/m2)
    cloud: Mapped[float]             # cloud_cover (%)
    precip_prob: Mapped[float] = mapped_column(default=0)
    apparent: Mapped[float] = mapped_column(default=0)
    hi: Mapped[float] = mapped_column(default=0)
    tw: Mapped[float] = mapped_column(default=0)       # psychrometric wet-bulb (Stull)
    tnwb: Mapped[float] = mapped_column(default=0)     # estimated natural wet-bulb
    tg: Mapped[float] = mapped_column(default=0)       # estimated globe temperature
    wbgt: Mapped[float] = mapped_column(default=0)     # estimated outdoor WBGT
    utci_proxy: Mapped[float] = mapped_column(default=0)


class HistoricalDaily(Base):
    """Synthetic historical daily weather + hospital load (>= 730 days)."""

    __tablename__ = "historical_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    d: Mapped[date] = mapped_column(Date, index=True)
    tmax: Mapped[float]
    tmin: Mapped[float]
    rh: Mapped[float]
    wind: Mapped[float]
    radiation: Mapped[float]
    wbgt_max: Mapped[float]
    hi_max: Mapped[float]
    utci_max: Mapped[float]
    night_recovery: Mapped[float] = mapped_column(default=0)
    consecutive_days: Mapped[int] = mapped_column(default=0)
    hospital_load_increase_pct: Mapped[float]
    heat_admissions: Mapped[int]


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    body_en: Mapped[str] = mapped_column(Text)
    body_kn: Mapped[str] = mapped_column(Text)
    channels: Mapped[list] = mapped_column(JSON, default=list)  # ["dashboard","sms","whatsapp","webhook"]
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft / Sent (simulated)
    sent_via: Mapped[list] = mapped_column(JSON, default=list)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True)  # None => city-level
    risk_level: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(20))  # Immediate / Today / Monitor
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending / In Progress / Completed
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HeatActionPlan(Base):
    __tablename__ = "heat_action_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    triggered_by: Mapped[str] = mapped_column(String(100), default="Command Centre Officer")
    status: Mapped[str] = mapped_column(String(20), default="Active")
    summary: Mapped[str] = mapped_column(Text)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    model_type: Mapped[str] = mapped_column(String(80))
    n_samples: Mapped[int] = mapped_column(default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_importance: Mapped[dict] = mapped_column(JSON, default=dict)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)