"use client";

import * as React from "react";

import { MessageList, type ChatMessage } from "@/components/chat/MessageList";
import { PromptInput } from "@/components/chat/PromptInput";
import { ScoreCard } from "@/components/score/ScoreCard";
import { HistoryList, type HistoryEntry } from "@/components/score/HistoryList";
import { friendlyMessageFor, type ErrorCode } from "@/lib/errors";
import { parseOldestAgeToMonths, parsePasswordCount } from "@/lib/validation";
import type { AgentScoreResponse, Band } from "@/lib/agent-client";

interface CheckResult extends AgentScoreResponse {
  id: string;
  previous_score: number | null;
  created_at: string;
}

type Step = "ask-count" | "ask-age" | "submitting" | "show-result";

const AGENT_GREETING =
  "Hi! Quick check-in: about how many passwords are you keeping right now?";
const AGENT_AGE_QUESTION =
  "Got it. And about how old is the oldest one — feel free to say something like \"6 months\" or \"3 years\"?";

const RETRY_COUNT = "I didn't catch a number there. Try a count like \"12\".";
const RETRY_AGE = "Hmm, I couldn't read that. Try \"3 years\" or \"6 months\".";

/**
 * Generate a unique message id for the in-memory chat transcript.
 *
 * @returns A short random string suitable as a React key.
 */
function nid(): string {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * Top-level chat surface for the password-health flow.
 *
 * Renders the running transcript, the input row, the score card after a
 * successful check, and the history list. Speaks to the BFF at
 * `POST /api/checks` and `GET /api/history`.
 */
export function ChatPane() {
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    { id: nid(), author: "agent", text: AGENT_GREETING },
  ]);
  const [step, setStep] = React.useState<Step>("ask-count");
  const [count, setCount] = React.useState<number | null>(null);
  const [result, setResult] = React.useState<CheckResult | null>(null);
  const [history, setHistory] = React.useState<HistoryEntry[]>([]);

  /**
   * Fetch the visitor's history once on mount and keep it in state for the
   * HistoryList. Failures fall back to an empty history (FR-012).
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
   * Append a message to the transcript.
   */
  function say(author: ChatMessage["author"], text: string) {
    setMessages((prev) => [...prev, { id: nid(), author, text }]);
  }

  /**
   * Handle the user's answer for the password-count question.
   */
  function onCountAnswer(raw: string) {
    say("user", raw);
    const parsed = parsePasswordCount(raw);
    if (parsed === null || parsed > 10_000) {
      say("agent", RETRY_COUNT);
      return;
    }
    setCount(parsed);
    setStep("ask-age");
    say("agent", AGENT_AGE_QUESTION);
  }

  /**
   * Handle the user's answer for the oldest-password-age question. On a
   * valid value, submit to the BFF and render the score card.
   */
  async function onAgeAnswer(raw: string) {
    say("user", raw);
    const months = parseOldestAgeToMonths(raw);
    if (months === null || months > 600 || count === null) {
      say("agent", RETRY_AGE);
      return;
    }

    setStep("submitting");
    try {
      const res = await fetch("/api/checks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          password_count: count,
          oldest_password_age_months: months,
        }),
      });

      if (!res.ok) {
        const env = (await res.json().catch(() => ({}))) as {
          code?: ErrorCode;
          message?: string;
        };
        const code = env.code ?? "INTERNAL_ERROR";
        say("system-error", env.message ?? friendlyMessageFor(code));
        setStep("ask-count");
        setCount(null);
        return;
      }

      const body = (await res.json()) as CheckResult;
      setResult(body);
      setHistory((prev) => [
        { id: body.id, score: body.score, band: body.band as Band, created_at: body.created_at },
        ...prev,
      ]);
      setStep("show-result");
    } catch {
      say("system-error", friendlyMessageFor("INTERNAL_ERROR"));
      setStep("ask-count");
      setCount(null);
    }
  }

  /**
   * Restart the conversation for another check (FR-010).
   */
  function startOver() {
    setResult(null);
    setCount(null);
    setStep("ask-count");
    setMessages([{ id: nid(), author: "agent", text: AGENT_GREETING }]);
  }

  const placeholder =
    step === "ask-count"
      ? "How many passwords?"
      : step === "ask-age"
        ? "How old is the oldest?"
        : "Tap restart for a fresh check";
  const submitting = step === "submitting";

  return (
    <div className="flex flex-col gap-4">
      <MessageList messages={messages} />

      {step !== "show-result" && (
        <PromptInput
          placeholder={placeholder}
          disabled={submitting}
          onSubmit={(value) =>
            step === "ask-count" ? onCountAnswer(value) : void onAgeAnswer(value)
          }
        />
      )}

      {step === "submitting" && (
        <p className="text-sm text-zinc-500">Crunching the numbers…</p>
      )}

      {step === "show-result" && result && (
        <>
          <ScoreCard
            score={result.score}
            band={result.band as Band}
            recommendations={result.recommendations}
            message={result.message}
            previousScore={result.previous_score}
          />
          <button
            type="button"
            onClick={startOver}
            className="self-start text-sm font-medium text-zinc-700 underline-offset-4 hover:underline"
          >
            Start a new check
          </button>
        </>
      )}

      <HistoryList entries={history} />
    </div>
  );
}
