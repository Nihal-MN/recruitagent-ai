"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type CandidateListItem } from "@/lib/api";
import { Badge, Card, CardBody, EmptyState, PageHeader, Spinner, StageBadge } from "@/components/ui";

export default function CandidatesPage() {
  const [query, setQuery] = useState("");
  const [skill, setSkill] = useState("");
  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      api.candidates
        .list({ query: query || undefined, skill: skill || undefined })
        .then(setCandidates)
        .catch(() => setCandidates([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, skill]);

  return (
    <>
      <PageHeader
        title="Candidates"
        subtitle="Synthetic demo dataset — 20 profiles. Skill filtering is canonicalised (e.g. “k8s” finds “Kubernetes”)."
        action={
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search name, headline, summary…"
              className="w-56 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400"
            />
            <input
              value={skill}
              onChange={(event) => setSkill(event.target.value)}
              placeholder="Skill (e.g. python)"
              className="w-40 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400"
            />
          </div>
        }
      />
      <Card>
        <CardBody className="p-0">
          {loading ? (
            <div className="flex items-center gap-2 px-5 py-8 text-xs text-slate-500">
              <Spinner size={14} /> loading candidates…
            </div>
          ) : candidates.length === 0 ? (
            <div className="px-5 py-6">
              <EmptyState title="No candidates match" hint="Try a different search or skill." />
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {candidates.map((candidate) => (
                <li key={candidate.id}>
                  <Link
                    href={`/candidates/${candidate.id}`}
                    className="flex items-start justify-between gap-4 px-5 py-4 transition-colors hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">{candidate.full_name}</p>
                        {candidate.in_pipeline ? <StageBadge stage={candidate.in_pipeline} /> : null}
                      </div>
                      <p className="mt-0.5 truncate text-xs text-slate-500">
                        {candidate.headline ?? "—"}
                        {candidate.location ? ` · ${candidate.location}` : ""}
                        {candidate.years_experience != null ? ` · ${candidate.years_experience} yrs` : ""}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {candidate.skills.slice(0, 8).map((name) => (
                          <Badge key={name} tone="slate" mono>
                            {name}
                          </Badge>
                        ))}
                        {candidate.skills.length > 8 ? (
                          <span className="text-[10px] text-slate-400">+{candidate.skills.length - 8} more</span>
                        ) : null}
                      </div>
                    </div>
                    <span className="mt-1 text-xs text-emerald-600">View →</span>
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
