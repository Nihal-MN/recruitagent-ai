/**
 * Typed API client for the RecruitAgent backend.
 * Errors carry the backend's structured { error: { code, message, detail } }.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  detail?: string | null;

  constructor(code: string, message: string, status: number, detail?: string | null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("network_error", `Cannot reach the API at ${API_BASE}. Is it running?`, 0);
  }
  if (!response.ok) {
    let code = "http_error";
    let message = `Request failed (${response.status})`;
    let detail: string | null = null;
    try {
      const body = await response.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        detail = body.error.detail ?? null;
      } else if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : message;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, message, response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ── types ────────────────────────────────────────────────────────────────────

export type AiMode = {
  mode: string;
  provider: string;
  provider_label: string;
  model: string;
  api_key_configured: boolean;
};

export type Health = {
  status: string;
  app: string;
  version: string;
  database: { status: string; dialect: string | null; detail: string | null };
  ai: AiMode;
  counts: Record<string, number>;
};

export type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type Message = {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  seq: number;
  created_at: string;
};

export type ToolExecution = {
  id: number;
  conversation_id: number;
  step_number: number;
  tool_name: string;
  tool_kind: string;
  args_json: Record<string, unknown> | null;
  status: string;
  error_code: string | null;
  result_summary: string | null;
  duration_ms: number | null;
  approval_id: number | null;
  created_at: string;
};

export type Approval = {
  id: number;
  conversation_id: number | null;
  tool_name: string;
  args_json: Record<string, unknown>;
  summary: string;
  status: string;
  decided_at: string | null;
  decided_by: string | null;
  executed_at: string | null;
  result_summary: string | null;
  error_code: string | null;
  created_at: string;
};

export type TurnResult = {
  conversation_id: number;
  final_text: string;
  stopped_reason: string;
  message_ids: number[];
  tool_execution_ids: number[];
  approval_ids: number[];
  error_code: string | null;
};

export type ConversationDetail = Conversation & {
  messages: Message[];
  tool_executions: ToolExecution[];
  approvals: Approval[];
};

export type ActivityEvent = {
  id: number;
  type: string;
  summary: string;
  conversation_id: number | null;
  approval_id: number | null;
  candidate_id: number | null;
  job_id: number | null;
  application_id: number | null;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type CandidateListItem = {
  id: number;
  full_name: string;
  headline: string | null;
  location: string | null;
  years_experience: number | null;
  skills: string[];
  in_pipeline: string | null;
};

export type CandidateDetail = {
  id: number;
  full_name: string;
  headline: string | null;
  location: string | null;
  years_experience: number | null;
  summary: string | null;
  skills: { name: string; normalized_name: string; category: string | null; evidence: string | null }[];
  experiences: {
    title: string | null;
    company: string | null;
    start_date: string | null;
    end_date: string | null;
    is_current: boolean;
  }[];
  applications: { id: number; job_id: number; job_title: string; stage: string }[];
  notes: { id: number; body: string; source: string; author: string; created_at: string }[];
  notes_count: number;
};

export type JobListItem = {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  seniority: string | null;
  domain: string | null;
  status: string;
  requirements_count: number;
  applications_count: number;
};

export type JobDetail = {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  seniority: string | null;
  domain: string | null;
  status: string;
  requirements: { id: number; kind: string; category: string; label: string; min_years: number | null }[];
  applications_count: number;
};

export type PipelineItem = {
  application_id: number;
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  job_title: string;
  stage: string;
  updated_at: string;
};

export type PipelineBoard = {
  columns: Record<string, PipelineItem[]>;
  total: number;
};

// ── client ───────────────────────────────────────────────────────────────────

export const api = {
  health: () => request<Health>("/health"),

  conversations: {
    list: () => request<Conversation[]>("/conversations"),
    create: (title?: string) =>
      request<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title: title ?? null }),
      }),
    get: (id: number) => request<ConversationDetail>(`/conversations/${id}`),
    sendMessage: (id: number, content: string) =>
      request<TurnResult>(`/conversations/${id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
  },

  approvals: {
    list: (status?: string) =>
      request<Approval[]>(`/approvals${status ? `?status=${status}` : ""}`),
    approve: (id: number, decidedBy = "recruiter") =>
      request<Approval>(`/approvals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ decided_by: decidedBy }),
      }),
    reject: (id: number, decidedBy = "recruiter") =>
      request<Approval>(`/approvals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ decided_by: decidedBy }),
      }),
  },

  activity: { list: (limit = 100) => request<ActivityEvent[]>(`/activity?limit=${limit}`) },

  traces: {
    list: (conversationId?: number, limit = 100) =>
      request<ToolExecution[]>(
        `/tool-executions?limit=${limit}${conversationId ? `&conversation_id=${conversationId}` : ""}`,
      ),
  },

  candidates: {
    list: (params?: { query?: string; skill?: string; limit?: number }) => {
      const query = new URLSearchParams();
      if (params?.query) query.set("query", params.query);
      if (params?.skill) query.set("skill", params.skill);
      query.set("limit", String(params?.limit ?? 50));
      return request<CandidateListItem[]>(`/candidates?${query.toString()}`);
    },
    get: (id: number) => request<CandidateDetail>(`/candidates/${id}`),
  },

  jobs: {
    list: () => request<JobListItem[]>("/jobs"),
    get: (id: number) => request<JobDetail>(`/jobs/${id}`),
  },

  pipeline: { get: (jobId?: number) => request<PipelineBoard>(`/pipeline${jobId ? `?job_id=${jobId}` : ""}`) },
};
