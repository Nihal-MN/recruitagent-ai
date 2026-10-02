"use client";

import { useCallback, useEffect, useRef, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError, type Approval, type Conversation, type ConversationDetail } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { ApprovalCard } from "@/components/ApprovalCard";
import { MarkdownLite } from "@/components/MarkdownLite";
import { ToolTracePanel } from "@/components/ToolTracePanel";
import { Badge, Button, Card, CardBody, CardHeader, Spinner } from "@/components/ui";

const SUGGESTIONS = [
  "Find candidates for the Senior Backend Engineer role",
  "Why does this candidate match?",
  "Generate screening questions for this candidate",
  "Show me the pipeline board",
  'Add a note: "Strong systems thinking — follow up about distributed experience."',
  "Move this candidate to INTERVIEW",
];

function AgentChatContent() {
  const searchParams = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [input, setInput] = useState(() => searchParams.get("q") ?? "");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalsById, setApprovalsById] = useState<Record<number, Approval>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  const refreshList = useCallback(async () => {
    try {
      setConversations(await api.conversations.list());
    } catch {
      /* the shell already surfaces API unreachability */
    }
  }, []);

  const openConversation = useCallback(async (id: number) => {
    setActiveId(id);
    const fetched = await api.conversations.get(id);
    setDetail(fetched);
    setApprovalsById((prev) => {
      const next = { ...prev };
      for (const approval of fetched.approvals) next[approval.id] = approval;
      return next;
    });
  }, []);

  useEffect(() => {
    let active = true;
    api.conversations
      .list()
      .then((list) => {
        if (!active) return;
        setConversations(list);
        // Restore the most recent conversation so context survives reloads.
        if (list.length > 0) {
          openConversation(list[0].id);
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [openConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [detail?.messages.length, sending]);

  async function ensureConversation(): Promise<number> {
    if (activeId) return activeId;
    const created = await api.conversations.create();
    setConversations((prev) => [created, ...prev]);
    setActiveId(created.id);
    return created.id;
  }

  async function send() {
    const content = input.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    try {
      const id = await ensureConversation();
      setInput("");
      await api.conversations.sendMessage(id, content);
      await openConversation(id);
      await refreshList();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The agent turn failed. Try again.");
    } finally {
      setSending(false);
    }
  }

  function onApprovalDecided(updated: Approval) {
    setApprovalsById((prev) => ({ ...prev, [updated.id]: updated }));
    if (activeId) api.conversations.get(activeId).then(setDetail).catch(() => undefined);
  }

  const messages = detail?.messages ?? [];
  const executions = detail?.tool_executions ?? [];

  return (
    <div className="flex gap-6">
      {/* ── Chat column ─────────────────────────────────────────────── */}
      <section className="min-w-0 flex-1">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">Agent Chat</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              The agent proposes; nothing changes without your approval.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="max-w-[220px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700"
              value={activeId ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                if (value) openConversation(Number(value));
                else {
                  setActiveId(null);
                  setDetail(null);
                }
              }}
            >
              <option value="">＋ New conversation</option>
              {conversations.map((conversation) => (
                <option key={conversation.id} value={conversation.id}>
                  {conversation.title} · {conversation.message_count} msgs
                </option>
              ))}
            </select>
            {detail ? (
              <Button variant="secondary" size="sm" onClick={() => openConversation(detail.id)}>
                Refresh
              </Button>
            ) : null}
          </div>
        </div>

        <Card className="flex h-[calc(100vh-330px)] min-h-[420px] flex-col">
          <CardBody className="scroll-slim flex-1 overflow-y-auto">
            {messages.length === 0 && !sending ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                <div className="max-w-md">
                  <p className="text-sm font-medium text-slate-700">
                    Ask about candidates, jobs, matches, screening or the pipeline.
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Every answer is grounded in tool results — pipeline moves and notes wait for your approval.
                  </p>
                </div>
                <div className="flex max-w-xl flex-wrap justify-center gap-2">
                  {SUGGESTIONS.slice(0, 4).map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setInput(suggestion)}
                      className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-emerald-400 hover:text-emerald-700"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                        message.role === "user"
                          ? "bg-emerald-600 text-white"
                          : "border border-slate-200 bg-white shadow-sm"
                      }`}
                    >
                      {message.role === "user" ? (
                        <p className="text-sm">{message.content}</p>
                      ) : (
                        <MarkdownLite text={message.content} />
                      )}
                      <p className={`mt-1 text-[10px] ${message.role === "user" ? "text-emerald-100" : "text-slate-400"}`}>
                        {message.role === "user" ? "you" : "recruitagent"} · {timeAgo(message.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
                {sending ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Spinner size={14} /> working through tools…
                  </div>
                ) : null}
                {(detail?.approvals ?? [])
                  .filter((approval) => approval.status === "PENDING" || approvalsById[approval.id]?.status !== "PENDING")
                  .filter((approval, index, array) => array.findIndex((other) => other.id === approval.id) === index)
                  .map((approval) => {
                    const current = approvalsById[approval.id] ?? approval;
                    if (current.status === "REJECTED" || current.status === "EXECUTED" || current.status === "FAILED") {
                      // show decided cards only if they were decided just now / this conversation is open
                      return (
                        <ApprovalCard key={current.id} approval={current} onDecided={onApprovalDecided} />
                      );
                    }
                    return <ApprovalCard key={current.id} approval={current} onDecided={onApprovalDecided} />;
                  })}
                <div ref={bottomRef} />
              </div>
            )}
          </CardBody>
          <div className="border-t border-slate-100 px-4 py-3">
            {error ? <p className="mb-2 text-xs text-rose-600">{error}</p> : null}
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send();
                  }
                }}
                rows={2}
                placeholder='e.g. "Find candidates for the Senior Backend Engineer role" — Enter to send, Shift+Enter for a new line'
                className="flex-1 resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none"
              />
              <Button onClick={send} disabled={!input.trim() || sending} loading={sending}>
                Send
              </Button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-600 hover:bg-emerald-50 hover:text-emerald-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </Card>
      </section>

      {/* ── Live tool trace ─────────────────────────────────────────── */}
      <aside className="hidden w-[340px] shrink-0 xl:block">
        <Card className="flex h-[calc(100vh-330px)] min-h-[420px] flex-col">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                Tool Trace <Badge tone="emerald">{executions.length}</Badge>
              </span>
            }
            subtitle="Safe operational events — no raw reasoning is ever recorded"
            action={
              <a href="/trace" className="text-xs font-medium text-emerald-600 hover:underline">
                View all
              </a>
            }
          />
          <CardBody className="scroll-slim flex-1 overflow-y-auto">
            <ToolTracePanel executions={[...executions].reverse()} compact />
          </CardBody>
        </Card>
      </aside>
    </div>
  );
}

export default function AgentChatPage() {
  return (
    <Suspense>
      <AgentChatContent />
    </Suspense>
  );
}
