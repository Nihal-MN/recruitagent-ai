"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type ToolExecution } from "@/lib/api";
import { ToolTracePanel } from "@/components/ToolTracePanel";
import { Badge, Card, CardBody, CardHeader, PageHeader, Spinner } from "@/components/ui";

function TraceContent() {
  const searchParams = useSearchParams();
  const [executions, setExecutions] = useState<ToolExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [conversationFilter, setConversationFilter] = useState<string>(searchParams.get("conversation_id") ?? "");

  useEffect(() => {
    let active = true;
    const conversationId = conversationFilter ? Number(conversationFilter) : undefined;
    api.traces
      .list(conversationId, 200)
      .then((rows) => {
        if (active) setExecutions(rows);
      })
      .catch(() => {
        if (active) setExecutions([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [conversationFilter]);

  return (
    <>
      <PageHeader
        title="Tool Trace"
        subtitle="Every tool call the agent made — name, arguments summary, status, duration and approval link. Deliberately operational, never chain-of-thought."
        action={
          <div className="flex items-center gap-2">
            <input
              value={conversationFilter}
              onChange={(event) => setConversationFilter(event.target.value.replace(/[^0-9]/g, ""))}
              placeholder="Filter: conversation id"
              className="w-44 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400"
            />
          </div>
        }
      />
      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              Recent executions <Badge tone="slate">{executions.length}</Badge>
            </span>
          }
          subtitle={conversationFilter ? `Conversation #${conversationFilter}` : "All conversations, newest first"}
        />
        <CardBody className="scroll-slim max-h-[calc(100vh-260px)] overflow-y-auto">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-xs text-slate-500">
              <Spinner size={14} /> loading trace…
            </div>
          ) : (
            <ToolTracePanel executions={executions} />
          )}
        </CardBody>
      </Card>
    </>
  );
}

export default function TracePage() {
  return (
    <Suspense>
      <TraceContent />
    </Suspense>
  );
}
