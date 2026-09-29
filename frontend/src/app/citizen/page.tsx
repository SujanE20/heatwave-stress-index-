"use client";

import { useEffect, useState } from "react";
import { Bell, Droplets, Droplet, MapPin, Shield, Snowflake, Sun, Thermometer } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmt } from "@/lib/utils";
import RiskBadge from "@/components/RiskBadge";
import { AlertNote, Badge, Card, CardContent, ErrorState, Select, Spinner } from "@/components/ui";

const KN: Record<string, string> = {
  header: "ನಿಮ್ಮ ವಾರ್ಡ್‌ನಲ್ಲಿ ಶಾಖ ಸ್ಥಿತಿ",
  cityRisk: "ನಗರದ ಅಪಾಯದ ಮಟ್ಟ",
  yourWard: "ನಿಮ್ಮ ವಾರ್ಡ್",
  current: "ಪ್ರಸ್ತುತ ಸ್ಥಿತಿ",
  advice: "ನಿಮಗಾಗಿ ಸಲಹೆಗಳು",
  advice1: "ಹೊರಾಂಗಣ ಕೆಲಸವನ್ನು ಬೆಳಿಗ್ಗೆ 6–10 ಮತ್ತು ಸಂಜೆ 4 ರ ನಂತರ ಮಾತ್ರ ಮಾಡಿ.",
  advice2: "ಆಗಾಗ್ಗೆ ನೀರು ಕುಡಿಯಿರಿ — ಬಾಯಾರಿಕೆಯಾಗದಿದ್ದರೂ ಸಹ.",
  advice3: "ವೃದ್ಧರು ಮತ್ತು ಅನಾರೋಗ್ಯದವರನ್ನು ದಿನಕ್ಕೆ ಎರಡು ಬಾರಿ ಪರಿಶೀಲಿಸಿ.",
  advice4: "ಶೀತಲ ಕೇಂದ್ರಕ್ಕೆ ಹೋಗಿ: ಸರ್ಕಾರಿ ಶಾಲೆ, ಸಮುದಾಯ ಭವನ.",
  cooling: "ಸಮೀಪದ ಶೀತಲ ಕೇಂದ್ರ",
  water: "ಸಮೀಪದ ನೀರಿನ ಕೇಂದ್ರ",
  alerts: "ನಿಮ್ಮ ವಾರ್ಡ್‌ಗೆ ಎಚ್ಚರಿಕೆಗಳು",
  disclaimer: "ಈ ಅಪ್ಲಿಕೇಶನ್ ನಿರ್ಧಾರ-ಸಹಾಯಕ ಮಾದರಿಯಾಗಿದೆ. ಸ್ಥಳೀಯ ದತ್ತಾಂಶದೊಂದಿಗೆ ಮೌಲ್ಯೀಕರಣ ಅಗತ್ಯ.",
};

export default function CitizenPage() {
  const { data: dashboard } = useApi(() => api.dashboard());
  const { data: alerts } = useApi(() => api.alerts());
  const [lang, setLang] = useState<"en" | "kn">("en");
  const [wardId, setWardId] = useState<string>("");
  const { data: wardRisk } = useApi(
    () => (wardId ? api.ward(wardId) : Promise.resolve(null)),
    [wardId]
  );

  const t = (en: string, kn: string) => (lang === "kn" ? kn : en);

  if (!dashboard) return <Spinner label="Loading…" />;

  const wards = dashboard.wards.sort((a, b) => b.score - a.score);
  const selected = wardRisk;
  const level = selected ? selected.final : (dashboard.risk.city_level === "maroon" ? { level: "maroon", label: "Extreme" } : { level: dashboard.risk.city_level, label: dashboard.risk.city_label });

  return (
    <div className="mx-auto max-w-md space-y-3 pb-10">
      {/* phone-style header */}
      <div className="rounded-t-2xl bg-slate-900 p-4 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-orange-400" />
            <div>
              <p className="text-sm font-extrabold">HEATSHIELD INDIA</p>
              <p className="text-[10px] text-slate-400">Mysore · citizen alerts</p>
            </div>
          </div>
          <button
            onClick={() => setLang(lang === "en" ? "kn" : "en")}
            className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200"
          >
            {lang === "en" ? "ಕನ್ನಡ" : "English"}
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-300">{t("Heat status in your ward", KN.header)}</p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
            {t("City risk level", KN.cityRisk)}
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <RiskBadge level={dashboard.risk.city_level} label={dashboard.risk.city_label} size="lg" />
            <span className="text-xs text-slate-500">
              {fmt(dashboard.current_conditions.t)}°C · HI {fmt(dashboard.current_conditions.hi)}°C
            </span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-orange-50 p-2">
              <Thermometer className="mx-auto h-4 w-4 text-orange-500" />
              <p className="mt-0.5 text-sm font-bold">{fmt(dashboard.current_conditions.t)}°C</p>
              <p className="text-[9px] text-slate-500">{t("Temperature", "ತಾಪಮಾನ")}</p>
            </div>
            <div className="rounded-lg bg-cyan-50 p-2">
              <Droplets className="mx-auto h-4 w-4 text-cyan-500" />
              <p className="mt-0.5 text-sm font-bold">{fmt(dashboard.current_conditions.rh)}%</p>
              <p className="text-[9px] text-slate-500">{t("Humidity", "ತೇವಾಂಶ")}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-2">
              <Sun className="mx-auto h-4 w-4 text-red-500" />
              <p className="mt-0.5 text-sm font-bold">{fmt(dashboard.current_conditions.wbgt)}°C</p>
              <p className="text-[9px] text-slate-500">WBGT</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
            {t("Select your ward", KN.yourWard)}
          </p>
          <Select value={wardId} onChange={setWardId}>
            <option value="">— {t("choose ward", "ವಾರ್ಡ್ ಆಯ್ಕೆಮಾಡಿ")} —</option>
            {wards.map((w) => (
              <option key={w.id} value={String(w.id)}>{w.code} · {w.name} ({w.label})</option>
            ))}
          </Select>

          {selected && (
            <div className="mt-3 space-y-3">
              <div className="flex items-center justify-between rounded-xl border-l-4 border-risk-red bg-slate-50 p-3">
                <div>
                  <p className="text-xs font-bold">{selected.ward_name}</p>
                  <p className="text-[10px] text-slate-500">Ward {selected.ward_code}</p>
                </div>
                <RiskBadge level={selected.final.level} label={selected.final.label} />
              </div>

              <AlertNote tone={selected.final.level === "red" || selected.final.level === "maroon" ? "danger" : selected.final.level === "orange" ? "warning" : "success"}
                title={t("What you should do", KN.advice)}>
                <ul className="list-disc pl-4">
                  <li>{t("Outdoor work only 6–10 AM and after 4 PM.", KN.advice1)}</li>
                  <li>{t("Drink water frequently — even if not thirsty.", KN.advice2)}</li>
                  <li>{t("Check elderly and sick family members twice a day.", KN.advice3)}</li>
                  <li>{t("Visit the cooling centre: Government School, Community Hall.", KN.advice4)}</li>
                </ul>
              </AlertNote>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-sky-50 p-3">
                  <p className="flex items-center gap-1 text-[10px] font-semibold text-sky-800">
                    <Snowflake className="h-3.5 w-3.5" /> {t("Nearest cooling centre", KN.cooling)}
                  </p>
                  <p className="mt-1 text-xs font-bold text-sky-900">{selected.nearest.cooling_centre.name}</p>
                  <p className="text-[10px] text-sky-700">{selected.nearest.cooling_centre.distance_km} km</p>
                </div>
                <div className="rounded-xl bg-cyan-50 p-3">
                  <p className="flex items-center gap-1 text-[10px] font-semibold text-cyan-800">
                    <Droplet className="h-3.5 w-3.5" /> {t("Nearest water point", KN.water)}
                  </p>
                  <p className="mt-1 text-xs font-bold text-cyan-900">{selected.nearest.water_point.name}</p>
                  <p className="text-[10px] text-cyan-700">{selected.nearest.water_point.distance_km} km</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* alerts for the ward */}
      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">
            <Bell className="h-3.5 w-3.5" /> {t("Alerts for your ward", KN.alerts)}
          </p>
          {(alerts ?? []).filter((a) => !wardId || a.ward_id === Number(wardId)).slice(0, 3).map((a) => (
            <div key={a.id} className="mb-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5">
              <p className="text-[11px] font-bold text-amber-900">{a.title}</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-amber-800">
                {lang === "kn" ? a.body_kn : a.body_en}
              </p>
              <Badge className="mt-1 bg-amber-100 text-amber-700">{a.status}</Badge>
            </div>
          ))}
          {(alerts ?? []).length === 0 && (
            <p className="text-xs text-slate-500">
              {t("No alerts yet — officials will publish ward alerts when the risk rises.", "ಇನ್ನೂ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ — ಅಪಾಯ ಹೆಚ್ಚಾದಾಗ ಅಧಿಕಾರಿಗಳು ಎಚ್ಚರಿಕೆ ಪ್ರಕಟಿಸುತ್ತಾರೆ.")}
            </p>
          )}
        </CardContent>
      </Card>

      <p className="flex items-center gap-1.5 px-2 text-[10px] text-slate-400">
        <MapPin className="h-3 w-3" />
        {t(KN.disclaimer, KN.disclaimer)}
      </p>
    </div>
  );
}