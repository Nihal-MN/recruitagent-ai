"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Approval } from "@/lib/api";
import { ApprovalCard } from "@/components/ApprovalCard";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, Spinner } from "@/components/ui";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.approvals
      .list()
      .then(setApprovals)
      .catch(() => setApprovals([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pending = approvals.filter((approval) => approval.status === "PENDING");
  const decided = approvals.filter((approval) => approval.status !== "PENDING");

  function onDecided(updated: Approval) {
    setApprovals((prev) => prev.map((approval) => (approval.id === updated.id ? updated : approval)));
  }

  return (
    <>
      <PageHeader
        title="Approvals"
        subtitle="The gate for every consequential write. Approving executes the exact proposed action — exactly once; rejecting changes nothing."
      />

      {loading ? (
        <div className="flex items-center gap-2 py-10 text-xs text-slate-500">
          <Spinner size={14} /> loading approvals…
        </div>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  Waiting on you <Badge tone="amber">{pending.length}</Badge>
                </span>
              }
            />
            <CardBody className="space-y-3">
              {pending.length === 0 ? (
                <EmptyState
                  title="Nothing waiting"
                  hint="Ask the agent to move a candidate or add a note — the proposal will show up here."
                />
              ) : (
                pending.map((approval) => (
                  <ApprovalCard key={approval.id} approval={approval} onDecided={onDecided} />
                ))
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  History <Badge tone="slate">{decided.length}</Badge>
                </span>
              }
              subtitle="Every decision is in the audit trail, with its outcome."
            />
            <CardBody className="space-y-3">
              {decided.length === 0 ? (
                <p className="text-xs text-slate-500">No decisions yet.</p>
              ) : (
                decided.map((approval) => <ApprovalCard key={approval.id} approval={approval} onDecided={onDecided} />)
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </>
  );
}
