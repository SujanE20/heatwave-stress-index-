"use client";

import { useState } from "react";
import { Database, Download, FlaskConical, RefreshCw, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import {
  AlertNote, Badge, Button, Card, CardContent, CardDescription, CardHeader,
  CardTitle, ErrorState, Input, Label, Select, Separator, Slider, Spinner, Tabs,
} from "@/components/ui";

export default function AdminPage() {
  const { data, loading, error, refresh } = useApi(() => api.settings());
  const { data: sources, refresh: refreshSources } = useApi(() => api.dataSources());
  const [tab, setTab] = useState("thresholds");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [thresholds, setThresholds] = useState<number[]>([20, 40, 60, 80]);
  const [provider, setProvider] = useState("demo");
  const [scenario, setScenario] = useState("severe_humid");
  const [vulnW, setVulnW] = useState<Record<string, number>>({});
  const [htsiW, setHtsiW] = useState<Record<string, number>>({});

  if (loading) return <Spinner label="Loading admin settings…" />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={refresh} />;

  const s = data.settings;

  // hydrate local editors once
  if (thresholds[0] !== s.risk_thresholds[0]) {
    setThresholds(s.risk_thresholds);
    setProvider(s.weather_provider);
    setScenario(s.demo_scenario);
    setVulnW(s.vuln_weights);
    setHtsiW(s.htsi_weights);
  }

  const save = async (patch: Record<string, any>, label: string) => {
    setBusy(true);
    try {
      const res = await api.updateSettings(patch);
      setMsg(`✅ ${label} saved. ${res.message}`);
      refresh();
      refreshSources();
    } catch (e: any) {
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const uploadFile = async (url: string, file: File, label: string) => {
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl()}${url}`, { method: "POST", body: fd });
      const body = await res.json().catch(() => ({}));
      setMsg(res.ok ? `✅ ${body.message || label}` : `⚠️ ${body.detail || res.statusText}`);
      refreshSources();
    } catch (e: any) {
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const downloadSample = async () => {
    const csv = await api.sampleCsv();
    const blob = new Blob([csv.content], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = csv.filename;
    a.click();
  };

  const retrain = async () => {
    setBusy(true);
    try {
      const res = await api.retrainModel();
      setMsg(`✅ Model retrained — ${res.metadata.model_type}, r² ${res.metadata.metrics?.r2 ?? "n/a"}, ${res.metadata.n_samples} samples.`);
      refreshSources();
    } catch (e: any) {
      setMsg(`⚠️ ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const model = sources?.model;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">Admin Settings</h1>
        <Badge className="bg-slate-100 text-slate-700">Demo control panel</Badge>
      </div>

      {msg && <AlertNote tone={msg.startsWith("⚠️") ? "warning" : "success"}>{msg}</AlertNote>}

      <Tabs
        tabs={[
          { key: "thresholds", label: "Risk thresholds" },
          { key: "weights", label: "Weights" },
          { key: "weather", label: "Weather provider" },
          { key: "data", label: "Data & uploads" },
          { key: "model", label: "ML model" },
          { key: "sources", label: "Data sources" },
          { key: "methodology", label: "Methodology" },
        ]}
        value={tab}
        onChange={setTab}
      />

      {/* thresholds */}
      {tab === "thresholds" && (
        <Card>
          <CardHeader>
            <CardTitle>Risk thresholds</CardTitle>
            <CardDescription>Upper bounds for Green / Yellow / Orange / Red. Everything above the last bound is Maroon/Extreme.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {thresholds.map((t, i) => (
              <Slider
                key={i}
                label={`${["Green", "Yellow", "Orange", "Red"][i]} → ${["Yellow", "Orange", "Red", "Maroon"][i]} at`}
                min={5} max={95} step={1} value={t}
                onChange={(v) => setThresholds((prev) => prev.map((x, j) => (j === i ? v : x)))}
              />
            ))}
            <div className="flex items-center gap-2 pt-2">
              <Button loading={busy} onClick={() => save({ risk_thresholds: thresholds }, "Thresholds")}>Save thresholds</Button>
              <Button variant="outline" onClick={() => setThresholds(data.defaults.risk_thresholds)}>Reset to defaults</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* weights */}
      {tab === "weights" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>HTSI weights</CardTitle>
              <CardDescription>Human Thermal Stress Index components (sum ≈ 1.0)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.entries(htsiW).map(([k, v]) => (
                <Slider key={k} label={k.replace(/_/g, " ")} min={0} max={0.6} step={0.05} value={v}
                  onChange={(nv) => setHtsiW((p) => ({ ...p, [k]: nv }))} />
              ))}
              <Button loading={busy} onClick={() => save({ htsi_weights: htsiW }, "HTSI weights")}>Save HTSI weights</Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Vulnerability weights</CardTitle>
              <CardDescription>Ward vulnerability factors (sum ≈ 1.0)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.entries(vulnW).map(([k, v]) => (
                <Slider key={k} label={k.replace(/_/g, " ")} min={0} max={0.5} step={0.05} value={v}
                  onChange={(nv) => setVulnW((p) => ({ ...p, [k]: nv }))} />
              ))}
              <Button loading={busy} onClick={() => save({ vuln_weights: vulnW }, "Vulnerability weights")}>Save vulnerability weights</Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* weather provider */}
      {tab === "weather" && (
        <Card>
          <CardHeader>
            <CardTitle>Weather provider</CardTitle>
            <CardDescription>Demo mode works fully offline with 4 realistic scenarios; Open-Meteo requires internet.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Provider</Label>
              <Select value={provider} onChange={setProvider}>
                <option value="demo">Demo weather generator (offline)</option>
                <option value="openmeteo">Open-Meteo live forecast (internet)</option>
              </Select>
            </div>
            {provider === "demo" && (
              <div>
                <Label>Demo scenario</Label>
                <Select value={scenario} onChange={setScenario}>
                  {Object.entries(data.scenarios).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </Select>
                <p className="mt-2 text-[11px] text-slate-500">
                  The “Severe Humid Heatwave” scenario creates Red/Extreme risk in vulnerable wards — ideal for the jury demo.
                </p>
              </div>
            )}
            <Button loading={busy} onClick={() => save({ weather_provider: provider, demo_scenario: scenario }, "Provider")}>
              Save provider
            </Button>
          </CardContent>
        </Card>
      )}

      {/* data uploads */}
      {tab === "data" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Upload ward GeoJSON</CardTitle>
              <CardDescription>Replace demo ward polygons with official municipal GIS data (FeatureCollection with properties: code, name, population, …)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                type="file" accept=".geojson,.json"
                className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-900 file:px-3 file:py-1.5 file:text-xs file:text-white"
                onChange={(e) => e.target.files?.[0] && uploadFile("/api/v1/admin/wards/geojson", e.target.files[0], "GeoJSON uploaded")}
              />
              <Button variant="outline" size="sm" disabled>Uploading replaces geometry for matching ward codes</Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Upload demographic CSV</CardTitle>
              <CardDescription>Columns: ward_code, ward_name, population, elderly_pct, outdoor_worker_density, informal_housing_pct, hospital_access_score, population_density, green_cover_pct, chronic_disease_pct, elevation_m, area_km2</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                type="file" accept=".csv"
                className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-900 file:px-3 file:py-1.5 file:text-xs file:text-white"
                onChange={(e) => e.target.files?.[0] && uploadFile("/api/v1/admin/wards/demographics", e.target.files[0], "CSV uploaded")}
              />
              <Button variant="outline" size="sm" onClick={downloadSample}>
                <Download className="h-3.5 w-3.5" /> Download sample CSV format
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* model */}
      {tab === "model" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><FlaskConical className="h-4 w-4" /> Hospital-load model</CardTitle>
            <CardDescription>Trained on 730+ days of synthetic history with a rule-based fallback</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button loading={busy} onClick={retrain}>
              <RefreshCw className="h-4 w-4" /> Retrain Demo Model
            </Button>
            {model ? (
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-[10px] uppercase text-slate-400">Type</p>
                  <p className="text-sm font-bold">{model.model_type}</p>
                  <p className="text-[10px] text-slate-400">trained {model.trained_at.slice(0, 10)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-[10px] uppercase text-slate-400">Samples / fit</p>
                  <p className="text-sm font-bold">{model.n_samples} days</p>
                  <p className="text-[10px] text-slate-400">R² {model.metrics.r2 ?? "—"} · MAE {model.metrics.mae ?? "—"}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-[10px] uppercase text-slate-400">Fallback</p>
                  <p className="text-sm font-bold">{model.fallback_used ? "Active" : "Not needed"}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Model not trained yet.</p>
            )}
            {model && model.feature_importance && Object.keys(model.feature_importance).length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-semibold text-slate-700">Feature importance</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(model.feature_importance).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => (
                    <Badge key={k} variant="secondary">{k}: {(v * 100).toFixed(1)}%</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* data sources */}
      {tab === "sources" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Database className="h-4 w-4" /> Data source status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {sources ? (
              <>
                <div className="grid gap-2 sm:grid-cols-3">
                  {Object.entries(sources.counts).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-slate-50 p-3">
                      <p className="text-[10px] uppercase text-slate-400">{k.replace(/_/g, " ")}</p>
                      <p className="text-lg font-bold">{v}</p>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-600">Provider: <b>{sources.weather_provider}</b>{sources.is_demo && " (offline demo)"} · scenario: {sources.scenario}</p>
                <p className="text-xs text-slate-600">{sources.postgis}</p>
                <p className="text-xs text-slate-600">{sources.health_data_policy}</p>
              </>
            ) : (
              <Spinner />
            )}
          </CardContent>
        </Card>
      )}

      {/* methodology */}
      {tab === "methodology" && (
        <Card>
          <CardHeader><CardTitle>Thermal & risk methodology</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-slate-700">
            <p><b>HTSI</b> — {data.methodology.htsi}</p>
            <Separator />
            <p><b>Vulnerability</b> — {data.methodology.vulnerability}</p>
            <Separator />
            <p><b>Final risk</b> — {data.methodology.final_risk}</p>
            <Separator />
            {data.methodology.safety.map((s: string, i: number) => (
              <p key={i} className="text-xs text-slate-500">• {s}</p>
            ))}
          </CardContent>
        </Card>
      )}

      <DisclaimerFooter />
    </div>
  );
}

function apiUrl() {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}