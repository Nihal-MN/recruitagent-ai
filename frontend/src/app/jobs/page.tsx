"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type JobListItem } from "@/lib/api";
import { Badge, Card, CardBody, PageHeader, Spinner } from "@/components/ui";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.jobs
      .list()
      .then(setJobs)
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader
        title="Jobs"
        subtitle="Five seeded roles from the demo dataset. Open one, then ask the agent to rank candidates for it."
      />
      <Card>
        <CardBody className="p-0">
          {loading ? (
            <div className="flex items-center gap-2 px-5 py-8 text-xs text-slate-500">
              <Spinner size={14} /> loading jobs…
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {jobs.map((job) => (
                <li key={job.id}>
                  <Link
                    href={`/jobs/${job.id}`}
                    className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-slate-50"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">{job.title}</p>
                        <Badge tone={job.status === "open" ? "emerald" : "slate"}>{job.status}</Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {job.company ?? "—"}
                        {job.location ? ` · ${job.location}` : ""}
                        {job.seniority ? ` · ${job.seniority}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-4 text-xs text-slate-500">
                      <span>
                        <strong className="font-semibold text-slate-700">{job.requirements_count}</strong> requirements
                      </span>
                      <span>
                        <strong className="font-semibold text-slate-700">{job.applications_count}</strong> in pipeline
                      </span>
                      <span className="text-emerald-600">View →</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </>
  );
}
