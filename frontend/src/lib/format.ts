export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 45) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function timeShort(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const STAGE_ORDER = ["NEW", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED"];

export const STAGE_TONE: Record<string, string> = {
  NEW: "slate",
  SCREENING: "sky",
  SHORTLISTED: "indigo",
  INTERVIEW: "violet",
  OFFER: "amber",
  HIRED: "emerald",
  REJECTED: "rose",
};

export const TOOL_STATUS_TONE: Record<string, string> = {
  SUCCEEDED: "emerald",
  FAILED: "rose",
  AWAITING_APPROVAL: "amber",
  REJECTED: "slate",
};

export const APPROVAL_STATUS_TONE: Record<string, string> = {
  PENDING: "amber",
  APPROVED: "sky",
  EXECUTING: "sky",
  EXECUTED: "emerald",
  REJECTED: "slate",
  FAILED: "rose",
};

export const ACTIVITY_TONE: Record<string, string> = {
  conversation_started: "slate",
  approval_requested: "amber",
  approval_approved: "sky",
  approval_rejected: "slate",
  tool_executed: "emerald",
  stage_moved: "indigo",
  note_added: "violet",
};

export function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
