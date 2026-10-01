"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type JobDetail } from "@/lib/api";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, Spinner } from "@/components/ui";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = Number(params.id);
    if (!Number.isFinite(id)) return;
    api.jobs
      .get(id)
      .then(setJob)
      .catch(() => setJob(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-10 text-xs text-slate-500">
        <Spinner size={14} /> loading job…
      </div>
    );
  }
  if (!job) {
    return <EmptyState title="Job not found" hint="It may not exist in the demo dataset." />;
  }

  const musts = job.requirements.filter((requirement) => requirement.kind === "must_have");
  const prefs = job.requirements.filter((requirement) => requirement.kind === "preferred");
  const askUrl = `/?q=${encodeURIComponent(`Find candidates for the ${job.title} role`)}`;

  return (
    <>
      <PageHeader
        title={job.title}
        subtitle={[job.company, job.location, job.seniority, job.domain].filter(Boolean).join(" · ")}
        action={
          <Link
            href={askUrl}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Ask the agent to rank candidates
          </Link>
        }
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Requirements"
            subtitle="Matching is deterministic — each requirement is met / partial / missing / unknown, with evidence."
          />
          <CardBody className="space-y-4">
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Must-haves ({musts.length})
              </p>
              <ul className="space-y-1.5">
                {musts.map((requirement) => (
                  <li key={requirement.id} className="flex items-center gap-2 text-sm text-slate-700">
                    <Badge tone="emerald" mono>
                      {requirement.category}
                    </Badge>
                    {requirement.label}
                    {requirement.min_years != null ? (
                      <span className="text-xs text-slate-400">≥ {requirement.min_years} yrs</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Preferred ({prefs.length})
              </p>
              <ul className="space-y-1.5">
                {prefs.map((requirement) => (
                  <li key={requirement.id} className="flex items-center gap-2 text-sm text-slate-600">
                    <Badge tone="slate" mono>
                      {requirement.category}
                    </Badge>
                    {requirement.label}
                  </li>
                ))}
              </ul>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Pipeline" subtitle={`${job.applications_count} application(s) in the demo dataset`} />
          <CardBody>
            <Link href="/trace" className="text-sm text-emerald-600 hover:underline">
              See the agent&apos;s recent tool calls →
            </Link>
          </CardBody>
        </Card>
      </div>
    </>
  );
}
