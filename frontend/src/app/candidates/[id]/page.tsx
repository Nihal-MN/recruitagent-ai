"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type CandidateDetail } from "@/lib/api";
import { timeShort } from "@/lib/format";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, Spinner, StageBadge } from "@/components/ui";

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = Number(params.id);
    if (!Number.isFinite(id)) return;
    api.candidates
      .get(id)
      .then(setCandidate)
      .catch(() => setCandidate(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-10 text-xs text-slate-500">
        <Spinner size={14} /> loading candidate…
      </div>
    );
  }
  if (!candidate) {
    return <EmptyState title="Candidate not found" hint="It may not exist in the demo dataset." />;
  }

  const askUrl = `/?q=Why does ${encodeURIComponent(candidate.full_name)} match the Senior Backend Engineer role?`;

  return (
    <>
      <PageHeader
        title={candidate.full_name}
        subtitle={[candidate.headline, candidate.location, candidate.years_experience != null ? `${candidate.years_experience} yrs experience` : null]
          .filter(Boolean)
          .join(" · ")}
        action={
          <Link
            href={askUrl}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Ask the agent about this candidate
          </Link>
        }
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader title="Summary" />
            <CardBody>
              <p className="whitespace-pre-line text-sm text-slate-700">{candidate.summary ?? "—"}</p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Skills & evidence" subtitle="Each skill links back to the line it was extracted from — no invented claims." />
            <CardBody className="space-y-3">
              {candidate.skills.map((skill) => (
                <div key={skill.name} className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Badge tone="emerald" mono>
                      {skill.name}
                    </Badge>
                    {skill.category ? <span className="text-[10px] uppercase tracking-wide text-slate-400">{skill.category}</span> : null}
                  </div>
                  {skill.evidence ? (
                    <p className="mt-1.5 border-l-2 border-emerald-300 pl-2 text-xs italic text-slate-600">
                      “{skill.evidence}”
                    </p>
                  ) : null}
                </div>
              ))}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Experience" />
            <CardBody className="space-y-2">
              {candidate.experiences.map((experience, index) => (
                <div key={index} className="flex items-baseline justify-between gap-3 text-sm">
                  <p className="text-slate-700">
                    <span className="font-medium text-slate-900">{experience.title ?? "Role"}</span>
                    {experience.company ? ` · ${experience.company}` : ""}
                  </p>
                  <p className="shrink-0 text-xs text-slate-400">
                    {experience.start_date ?? "?"} — {experience.is_current ? "present" : (experience.end_date ?? "?")}
                  </p>
                </div>
              ))}
            </CardBody>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Pipeline" subtitle="Applications in the demo dataset" />
            <CardBody className="space-y-2">
              {candidate.applications.length === 0 ? (
                <p className="text-xs text-slate-500">Not in any pipeline yet.</p>
              ) : (
                candidate.applications.map((application) => (
                  <div key={application.id} className="flex items-center justify-between gap-2">
                    <Link href={`/jobs/${application.job_id}`} className="text-sm text-slate-700 underline-offset-2 hover:underline">
                      {application.job_title}
                    </Link>
                    <StageBadge stage={application.stage} />
                  </div>
                ))
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Notes" subtitle={`${candidate.notes_count} note(s) — agent notes arrive via approvals`} />
            <CardBody className="space-y-3">
              {candidate.notes.length === 0 ? (
                <p className="text-xs text-slate-500">No notes yet.</p>
              ) : (
                candidate.notes.map((note) => (
                  <div key={note.id} className="rounded-lg bg-slate-50 px-3 py-2">
                    <p className="text-xs text-slate-700">{note.body}</p>
                    <p className="mt-1 text-[10px] text-slate-400">
                      {note.source === "agent" ? "agent (approved)" : note.author} · {timeShort(note.created_at)}
                    </p>
                  </div>
                ))
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </>
  );
}
