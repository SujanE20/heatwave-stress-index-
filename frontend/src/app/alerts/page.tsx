"use client";

import { useState } from "react";
import { CheckCircle2, Globe, Mail, MessageSquare, Radio, Send, ShieldAlert, Smartphone } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtTime } from "@/lib/utils";
import type { Alert } from "@/lib/types";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import {
  AlertNote, Badge, Button, Card, CardContent, CardDescription, CardHeader,
  CardTitle, ErrorState, Select, Spinner, Tabs,
} from "@/components/ui";

type PreviewKey = "en" | "kn" | "sms" | "wa";

const PREVIEW_TABS: { key: PreviewKey; label: string }[] = [
  { key: "en", label: "English" },
  { key: "kn", label: "ಕನ್ನಡ" },
  { key: "sms", label: "SMS preview" },
  { key: "wa", label: "WhatsApp" },
];

export default function AlertsPage() {
  const { data: alerts, loading, error, refresh } = useApi(() => api.alerts());
  const [minLevel, setMinLevel] = useState("orange");
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const [view, setView] = useState<PreviewKey>("en");

  const generate = async () => {
    setBusy("generate");
    try {
      const res = await api.generateAlerts(minLevel);
      setNote({ tone: "success", text: `Generated ${res.generated} bilingual alerts (drafts). Use “Simulate send” to mark delivery.` });
      refresh();
    } catch (e: any) {
      setNote({ tone: "warning", text: `⚠️ ${e.message}` });
    } finally {
      setBusy(null);
    }
  };

  const sendOne = async (a: Alert) => {
    setBusy(`send-${a.id}`);
    try {
      const res = await api.sendAlerts([a.id], ["sms", "whatsapp", "webhook"]);
      setNote({ tone: "success", text: `Message to Ward ${a.ward_id} delivered (simulated) via ${res.alerts[0].sent_via.map((s: any) => s.channel).join(", ")}.` });
      refresh();
    } catch (e: any) {
      setNote({ tone: "warning", text: `⚠️ ${e.message}` });
    } finally {
      setBusy(null);
    }
  };

  const sendAll = async () => {
    setBusy("send");
    try {
      const draftIds = (alerts ?? []).filter((a) => a.status === "Draft").map((a) => a.id);
      const res = await api.sendAlerts(draftIds, ["sms", "whatsapp", "webhook"]);
      setNote({ tone: "success", text: `Simulated delivery of ${res.sent} alerts. No real messages were sent.` });
      refresh();
    } catch (e: any) {
      setNote({ tone: "warning", text: `⚠️ ${e.message}` });
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <Spinner label="Loading alerts…" />;
  if (error) return <ErrorState message={error} onRetry={refresh} />;

  const drafts = (alerts ?? []).filter((a) => a.status === "Draft");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">Alerts Centre</h1>
        <Badge className="bg-slate-100 text-slate-700">{drafts.length} drafts · {(alerts ?? []).length} total</Badge>
      </div>

      <AlertNote tone="warning" title="No real messages are ever sent">
        SMS, WhatsApp and webhook delivery is <b>simulated</b>. Integrate real gateways (e.g. NDMA bulk SMS, WhatsApp Business API)
        before operational deployment.
      </AlertNote>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Generate bilingual alerts</CardTitle>
          <CardDescription>Alerts are generated for wards at or above the selected risk level, in English and Kannada</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-48">
              <Select value={minLevel} onChange={setMinLevel} label="Minimum risk level">
                <option value="orange">High (Orange) and above</option>
                <option value="red">Very High (Red) and above</option>
                <option value="maroon">Extreme (Maroon) only</option>
              </Select>
            </div>
            <Button loading={busy === "generate"} onClick={generate}>
              <Send className="h-4 w-4" /> Generate draft alerts
            </Button>
            <Button variant="secondary" loading={busy === "send"} onClick={sendAll} disabled={drafts.length === 0}>
              <Radio className="h-4 w-4" /> Simulate send ({drafts.length} drafts)
            </Button>
            <Tabs
              tabs={PREVIEW_TABS}
              value={view}
              onChange={(k) => setView(k as PreviewKey)}
            />
          </div>
          {note && (
            <AlertNote tone={note.tone} title={note.tone === "success" ? "Delivery complete" : "Action needed"}>
              {note.text}
            </AlertNote>
          )}
        </CardContent>
      </Card>

      {alerts && alerts.length === 0 && (
        <AlertNote tone="info" title="No alerts yet">Click “Generate draft alerts” to create bilingual alerts for the current risk situation.</AlertNote>
      )}

      <div className="space-y-3">
        {(alerts ?? []).map((a) => (
          <Card key={a.id}>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={a.severity.includes("extreme") || a.severity.includes("danger") ? "destructive" : "secondary"}>
                  {a.severity}
                </Badge>
                <p className="text-sm font-bold text-slate-900">{a.title}</p>
                <span className="text-[11px] text-slate-400">{fmtTime(a.ts)}</span>
                <div className="ml-auto flex items-center gap-2">
                  {a.channels.map((c) => (
                    <span key={c} className="flex items-center gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                      {c === "sms" ? <MessageSquare className="h-3 w-3" /> : c === "whatsapp" ? <Globe className="h-3 w-3" /> : c === "webhook" ? <Radio className="h-3 w-3" /> : <Mail className="h-3 w-3" />}
                      {c}
                    </span>
                  ))}
                  <Badge variant={a.status === "Sent (simulated)" ? "secondary" : "outline"}>{a.status}</Badge>
                  {a.status === "Draft" ? (
                    <Button size="sm" variant="default" loading={busy === `send-${a.id}`} onClick={() => sendOne(a)}>
                      <Smartphone className="h-3.5 w-3.5" /> Send now
                    </Button>
                  ) : (
                    a.sent_via.length > 0 && (
                      <span className="flex items-center gap-1 text-[11px] text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" /> {a.sent_via.length} channel{a.sent_via.length > 1 ? "s" : ""} delivered
                      </span>
                    )
                  )}
                </div>
              </div>

              <div className="mt-2 grid gap-2 lg:grid-cols-2">
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {view === "sms" ? "SMS preview" : view === "wa" ? "WhatsApp message" : view === "kn" ? "ಕನ್ನಡ" : "English"}
                  </p>
                  {view === "sms" && (
                    <div className="mt-1 flex items-start gap-2">
                      <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                      <p className="text-xs leading-relaxed text-slate-800">{a.sms}</p>
                    </div>
                  )}
                  {view === "wa" && (
                    <div className="mt-1 rounded-xl rounded-tl-sm bg-emerald-50 p-3 ring-1 ring-emerald-200">
                      <p className="whitespace-pre-line text-xs leading-relaxed text-slate-800">{a.whatsapp}</p>
                    </div>
                  )}
                  {view === "en" && <p className="mt-1 text-xs leading-relaxed text-slate-700">{a.body_en}</p>}
                  {view === "kn" && <p className="mt-1 text-xs leading-relaxed text-slate-700">{a.body_kn}</p>}
                </div>
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                    {view === "sms" ? "WhatsApp message" : view === "wa" ? "SMS preview" : view === "kn" ? "English" : "ಕನ್ನಡ"}
                  </p>
                  {view === "sms" && (
                    <div className="mt-1 rounded-xl rounded-tl-sm bg-emerald-50 p-3 ring-1 ring-emerald-200">
                      <p className="whitespace-pre-line text-xs leading-relaxed text-slate-800">{a.whatsapp}</p>
                    </div>
                  )}
                  {view === "wa" && (
                    <div className="mt-1 flex items-start gap-2">
                      <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                      <p className="text-xs leading-relaxed text-slate-800">{a.sms}</p>
                    </div>
                  )}
                  {view === "en" && <p className="mt-1 text-xs leading-relaxed text-slate-700">{a.body_kn}</p>}
                  {view === "kn" && <p className="mt-1 text-xs leading-relaxed text-slate-700">{a.body_en}</p>}
                </div>
              </div>

              {a.status === "Sent (simulated)" && a.sent_via.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-emerald-700">
                  {a.sent_via.map((s) => (
                    <span key={s.channel} className="rounded bg-emerald-50 px-1.5 py-0.5">
                      {s.channel}: {s.status}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <DisclaimerFooter />
    </div>
  );
}