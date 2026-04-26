"use client";

import * as React from "react";

import { MessageList, type ChatMessage as UiChatMessage } from "@/components/chat/MessageList";
import { PromptInput } from "@/components/chat/PromptInput";
import { ScoreCard } from "@/components/score/ScoreCard";
import { HistoryList, type HistoryEntry } from "@/components/score/HistoryList";
import { friendlyMessageFor, type ErrorCode } from "@/lib/errors";
import type { Band, Recommendation } from "@/lib/agent-client";

interface AgentChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ResultPayload {
  type: "result";
  id: string;
  score: number;
  band: Band;
  recommendations: Recommendation[];
  message: string;
  previous_score: number | null;
  created_at: string;
}

const GREETING =
  "Hi! Two quick questions to score your password health: roughly how many passwords are you keeping right now?";

/**
 * Generate a unique id for the in-memory chat transcript.
 *
 * @returns A short random string suitable as a React key.
 */
function nid(): string {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * Top-level chat surface.
 *
 * Maintains a free-form conversation with the agent, posting the entire
 * running history to `/api/checks` on every user message. The agent
 * decides when it has enough information to compute the score; until
 * then we just relay its replies. When a `result` lands, we show the
 * score card and refresh the history list.
 */
export function ChatPane() {
  const [agentMessages, setAgentMessages] = React.useState<AgentChatMessage[]>([
    { role: "assistant", content: GREETING },
  ]);
  const [uiMessages, setUiMessages] = React.useState<UiChatMessage[]>([
    { id: nid(), author: "agent", text: GREETING },
  ]);
  const [submitting, setSubmitting] = React.useState(false);
  const [result, setResult] = React.useState<ResultPayload | null>(null);
  const [history, setHistory] = React.useState<HistoryEntry[]>([]);

  /**
   * Fetch the visitor's history once on mount.
   */
  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/history", { cache: "no-store" });
        if (!res.ok) return;
        const body = (await res.json()) as { history: HistoryEntry[] };
        if (!cancelled) setHistory(body.history ?? []);
      } catch {
        // Friendly empty state handles this; never surface a raw error.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  /**
   * Append a UI bubble to the visible transcript.
   */
  function pushUi(author: UiChatMessage["author"], text: string) {
    setUiMessages((prev) => [...prev, { id: nid(), author, text }]);
  }

  /**
   * Send the next user turn: append locally, POST history, render reply.
   */
  async function onSubmit(text: string) {
    const userTurn: AgentChatMessage = { role: "user", content: text };
    const nextAgentMessages = [...agentMessages, userTurn];
    setAgentMessages(nextAgentMessages);
    pushUi("user", text);

    setSubmitting(true);
    try {
      const res = await fetch("/api/checks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextAgentMessages }),
      });

      if (!res.ok) {
        const env = (await res.json().catch(() => ({}))) as {
          code?: ErrorCode;
          message?: string;
        };
        const code = env.code ?? "INTERNAL_ERROR";
        pushUi("system-error", env.message ?? friendlyMessageFor(code));
        return;
      }

      const body = (await res.json()) as
        | { type: "message"; content: string }
        | ResultPayload;

      if (body.type === "message") {
        setAgentMessages((prev) => [
          ...prev,
          { role: "assistant", content: body.content },
        ]);
        pushUi("agent", body.content);
        return;
      }

      // Result path: append the message bubble, render the score card,
      // refresh history.
      setAgentMessages((prev) => [
        ...prev,
        { role: "assistant", content: body.message },
      ]);
      pushUi("agent", body.message);
      setResult(body);
      setHistory((prev) => [
        {
          id: body.id,
          score: body.score,
          band: body.band,
          created_at: body.created_at,
        },
        ...prev,
      ]);
    } catch {
      pushUi("system-error", friendlyMessageFor("INTERNAL_ERROR"));
    } finally {
      setSubmitting(false);
    }
  }

  /**
   * Reset the conversation for a fresh check.
   */
  function startOver() {
    setResult(null);
    setAgentMessages([{ role: "assistant", content: GREETING }]);
    setUiMessages([{ id: nid(), author: "agent", text: GREETING }]);
  }

  return (
    <div className="flex flex-col gap-4">
      <MessageList messages={uiMessages} />

      <PromptInput
        placeholder={
          result ? "Tap Start over for another check" : "Type your answer…"
        }
        disabled={submitting || result !== null}
        onSubmit={onSubmit}
      />

      {submitting && <p className="text-sm text-zinc-500">Thinking…</p>}

      {result && (
        <>
          <ScoreCard
            score={result.score}
            band={result.band}
            recommendations={result.recommendations}
            message={result.message}
            previousScore={result.previous_score}
          />
          <button
            type="button"
            onClick={startOver}
            className="self-start text-sm font-medium text-zinc-700 underline-offset-4 hover:underline"
          >
            Start over
          </button>
        </>
      )}

      <HistoryList entries={history} />
    </div>
  );
}
