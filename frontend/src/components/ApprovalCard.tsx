"use client";

import { useState } from "react";
import { api, ApiError, type Approval } from "@/lib/api";
import { timeShort, titleCase } from "@/lib/format";
import { ApprovalStatusBadge, Button } from "@/components/ui";

function ArgChips({ args }: { args: Record<string, unknown> }) {
  const entries = Object.entries(args).filter(([, value]) => value != null && value !== "");
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span key={key} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
          {key}: {String(value).length > 60 ? `${String(value).slice(0, 57)}…` : String(value)}
        </span>
      ))}
    </div>
  );
}

export function ApprovalCard({
  approval,
  onDecided,
}: {
  approval: Approval;
  onDecided?: (updated: Approval) => void;
}) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pending = approval.status === "PENDING";

  async function decide(action: "approve" | "reject") {
    setBusy(action);
    setError(null);
    try {
      const updated = action === "approve" ? await api.approvals.approve(approval.id) : await api.approvals.reject(approval.id);
      onDecided?.(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      className={`rounded-xl border px-4 py-3 shadow-sm ${
        pending ? "border-amber-200 bg-amber-50/60" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] font-semibold text-slate-500">#{approval.id}</span>
        <span className="font-mono text-[11px] text-slate-600">{approval.tool_name}</span>
        <ApprovalStatusBadge status={approval.status} />
        <span className="ml-auto text-[10px] text-slate-400">{timeShort(approval.created_at)}</span>
      </div>

      <p className="mt-2 text-sm font-medium text-slate-800">{approval.summary}</p>
      <div className="mt-2">
        <ArgChips args={approval.args_json} />
      </div>

      {pending ? (
        <p className="mt-2 text-[11px] text-amber-700">
          Nothing changes until you decide. Approval executes the exact action above — exactly once.
        </p>
      ) : null}

      {approval.result_summary ? (
        <p className="mt-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">
          {approval.status === "FAILED" ? "✕ " : "✓ "}
          {approval.result_summary}
        </p>
      ) : null}

      {error ? <p className="mt-2 text-xs text-rose-600">{error}</p> : null}

      <div className="mt-3 flex items-center gap-2">
        {pending ? (
          <>
            <Button size="sm" onClick={() => decide("approve")} loading={busy === "approve"} disabled={busy !== null}>
              Approve &amp; execute
            </Button>
            <Button size="sm" variant="secondary" onClick={() => decide("reject")} loading={busy === "reject"} disabled={busy !== null}>
              Reject
            </Button>
          </>
        ) : (
          <span className="text-[11px] text-slate-500">
            {titleCase(approval.status)}
            {approval.decided_by ? ` by ${approval.decided_by}` : ""}
            {approval.decided_at ? ` · ${timeShort(approval.decided_at)}` : ""}
          </span>
        )}
      </div>
    </div>
  );
}
