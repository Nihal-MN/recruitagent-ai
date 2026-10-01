"use client";

import { useEffect, useState } from "react";
import { API_BASE, api, type Health } from "@/lib/api";
import { Badge, Card, CardBody, CardHeader, PageHeader, Spinner } from "@/components/ui";

export default function HealthPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-10 text-xs text-slate-500">
        <Spinner size={14} /> checking system…
      </div>
    );
  }

  if (!health) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-rose-600">
            API unreachable at <code className="font-mono">{API_BASE}</code>. Start the stack and reload.
          </p>
        </CardBody>
      </Card>
    );
  }

  const demo = health.ai.provider === "demo" || !health.ai.api_key_configured;

  return (
    <>
      <PageHeader title="System Health" subtitle="Honest, live status — including which AI path is actually running." />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="AI mode" subtitle="How the agent loop is currently powered" />
          <CardBody>
            <div className={`rounded-xl border px-4 py-3 ${demo ? "border-amber-200 bg-amber-50" : "border-emerald-200 bg-emerald-50"}`}>
              <p className={`text-sm font-semibold ${demo ? "text-amber-800" : "text-emerald-800"}`}>
                {demo ? "Deterministic demo agent" : "OpenAI tool calling"}
              </p>
              <p className={`mt-1 text-xs ${demo ? "text-amber-700" : "text-emerald-700"}`}>
                {demo
                  ? "No API key configured — the deterministic provider drives the SAME orchestrator, tools, approvals and evals. Everything works offline; nothing is faked."
                  : `Live tool calling via ${health.ai.provider_label} · model ${health.ai.model}`}
              </p>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div>
                <dt className="text-slate-400">Provider</dt>
                <dd className="font-mono text-slate-700">{health.ai.provider}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Model</dt>
                <dd className="font-mono text-slate-700">{health.ai.model}</dd>
              </div>
              <div>
                <dt className="text-slate-400">API key configured</dt>
                <dd className="font-mono text-slate-700">{String(health.ai.api_key_configured)}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Version</dt>
                <dd className="font-mono text-slate-700">{health.version}</dd>
              </div>
            </dl>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Database" subtitle="Live connection + demo dataset counts" />
          <CardBody>
            <div className="flex items-center gap-2">
              <Badge tone={health.database.status === "ok" ? "emerald" : "rose"}>{health.database.status}</Badge>
              <span className="font-mono text-xs text-slate-600">{health.database.dialect}</span>
            </div>
            {health.database.detail ? <p className="mt-2 text-xs text-rose-600">{health.database.detail}</p> : null}
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              {Object.entries(health.counts).map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <dt className="text-slate-500">{label.replace(/_/g, " ")}</dt>
                  <dd className="font-mono text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Developer surface" subtitle="The same API the UI uses" />
          <CardBody className="flex flex-wrap items-center gap-4 text-sm">
            <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline">
              OpenAPI docs →
            </a>
            <a href={`${API_BASE}/api/v1/health`} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline">
              Raw health JSON →
            </a>
            <span className="text-xs text-slate-400">
              No auth by design (local demo) — see SECURITY.md before exposing anywhere public.
            </span>
          </CardBody>
        </Card>
      </div>
    </>
  );
}
