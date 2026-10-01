"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ActivityEvent } from "@/lib/api";
import { ACTIVITY_TONE, timeShort, titleCase } from "@/lib/format";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, Spinner } from "@/components/ui";

export default function ActivityPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.activity
      .list(200)
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader
        title="Activity"
        subtitle="The append-only audit trail: proposals → decisions → executions. This is where “exactly once” becomes visible."
      />
      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              Timeline <Badge tone="slate">{events.length}</Badge>
            </span>
          }
        />
        <CardBody className="scroll-slim max-h-[calc(100vh-260px)] overflow-y-auto">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-xs text-slate-500">
              <Spinner size={14} /> loading activity…
            </div>
          ) : events.length === 0 ? (
            <EmptyState title="No activity yet" hint="Agent turns, approvals and executions will appear here." />
          ) : (
            <ol className="relative space-y-4 border-l border-slate-200 pl-5">
              {events.map((event) => (
                <li key={event.id} className="relative">
                  <span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-300" />
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={ACTIVITY_TONE[event.type] ?? "slate"}>{titleCase(event.type)}</Badge>
                    <span className="text-[10px] text-slate-400">{timeShort(event.created_at)}</span>
                    {event.conversation_id ? (
                      <span className="text-[10px] text-slate-400">conv #{event.conversation_id}</span>
                    ) : null}
                    {event.approval_id ? (
                      <Link href="/approvals" className="text-[10px] font-medium text-emerald-600 hover:underline">
                        approval #{event.approval_id}
                      </Link>
                    ) : null}
                    {event.candidate_id ? (
                      <Link href={`/candidates/${event.candidate_id}`} className="text-[10px] font-medium text-emerald-600 hover:underline">
                        candidate #{event.candidate_id}
                      </Link>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-slate-700">{event.summary}</p>
                </li>
              ))}
            </ol>
          )}
        </CardBody>
      </Card>
    </>
  );
}
