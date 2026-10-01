"use client";

import Link from "next/link";
import type { ToolExecution } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { KindBadge, ToolStatusBadge } from "@/components/ui";

/**
 * Safe operational trace — tool name, sanitized args summary, status,
 * duration, result summary, approval state and timestamps.
 * It NEVER displays model reasoning/chain-of-thought (there is none stored).
 */
export function ToolTracePanel({
  executions,
  compact = false,
  emptyHint = "No tool calls yet — ask the agent to find candidates or explain a match.",
}: {
  executions: ToolExecution[];
  compact?: boolean;
  emptyHint?: string;
}) {
  if (executions.length === 0) {
    return <p className="px-1 py-2 text-xs text-slate-500">{emptyHint}</p>;
  }
  return (
    <ol className="space-y-2">
      {executions.map((execution) => (
        <li
          key={execution.id}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs shadow-sm"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="grid h-5 w-5 place-items-center rounded bg-slate-900 font-mono text-[10px] font-semibold text-white">
              {execution.step_number}
            </span>
            <span className="font-mono text-[12px] font-semibold text-slate-800">
              {execution.tool_name}
            </span>
            <KindBadge kind={execution.tool_kind} />
            <ToolStatusBadge status={execution.status} />
            {execution.duration_ms != null ? (
              <span className="ml-auto font-mono text-[10px] text-slate-400">{execution.duration_ms}ms</span>
            ) : null}
          </div>
          {execution.result_summary ? (
            <p className={`mt-1.5 text-slate-600 ${compact ? "line-clamp-2" : ""}`}>{execution.result_summary}</p>
          ) : null}
          <div className="mt-1.5 flex items-center gap-3 text-[10px] text-slate-400">
            <span>{timeAgo(execution.created_at)}</span>
            {execution.error_code ? <span className="font-mono text-rose-500">{execution.error_code}</span> : null}
            {execution.approval_id ? (
              <Link href="/approvals" className="font-medium text-emerald-600 hover:underline">
                approval #{execution.approval_id}
              </Link>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
