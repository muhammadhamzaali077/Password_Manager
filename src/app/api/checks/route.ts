import { Prisma } from "@prisma/client";
import { NextResponse, type NextRequest } from "next/server";

import { requestChat, type ChatTurnResponse } from "@/lib/agent-client";
import { toEnvelope } from "@/lib/errors";
import { prisma } from "@/lib/prisma";
import { getOrCreateVisitor } from "@/lib/session";
import { ChatRequestSchema } from "@/lib/validation";

const MAX_HISTORY_PER_VISITOR = 50;

/**
 * `POST /api/checks` — chat-style entrypoint.
 *
 * Forwards the running message history to the Python agent. If the agent
 * comes back with a `result` (it called the score tool), the BFF persists
 * a ScoreSubmission, prunes old rows, and returns an enriched payload
 * that includes the visitor's `previous_score` for US2 acknowledgements.
 * Otherwise it just relays the chat reply to the client.
 *
 * The whole route runs inside a top-level try/catch so any unexpected
 * exception is surfaced as the friendly INTERNAL_ERROR envelope rather
 * than escaping to Next.js's default empty-body 500 handler
 * (Constitution IV).
 */
export async function POST(request: NextRequest) {
  try {
    let raw: unknown;
    try {
      raw = await request.json();
    } catch {
      return toEnvelope("INVALID_INPUT", 400);
    }

    const parsed = ChatRequestSchema.safeParse(raw);
    if (!parsed.success) return toEnvelope("INVALID_INPUT", 400);

    const { visitorId } = await getOrCreateVisitor();

    let agentResponse: ChatTurnResponse;
    try {
      agentResponse = await requestChat({ messages: parsed.data.messages });
    } catch (err) {
      const e = err as { code?: string; message?: string };
      const code = (e.code ?? "INTERNAL_ERROR") as
        | "INVALID_INPUT"
        | "AGENT_TIMEOUT"
        | "AGENT_FORMAT_ERROR"
        | "RATE_LIMITED"
        | "INTERNAL_ERROR";
      const status =
        code === "INVALID_INPUT"
          ? 400
          : code === "AGENT_TIMEOUT"
            ? 504
            : code === "AGENT_FORMAT_ERROR"
              ? 502
              : code === "RATE_LIMITED"
                ? 429
                : 500;
      return toEnvelope(code, status);
    }

    if (agentResponse.type === "message") {
      return NextResponse.json({
        type: "message",
        content: agentResponse.content,
      });
    }

    // Result path — persist and enrich.
    const previous = await prisma.scoreSubmission.findFirst({
      where: { visitorId },
      orderBy: { createdAt: "desc" },
      select: { score: true },
    });

    const submission = await prisma.scoreSubmission.create({
      data: {
        visitorId,
        passwordCount: agentResponse.password_count,
        oldestPasswordAgeMonths: agentResponse.oldest_password_age_months,
        score: agentResponse.score,
        band: agentResponse.band,
        recommendations: agentResponse.recommendations as unknown as Prisma.InputJsonValue,
      },
    });

    // Best-effort prune; failure here must not break the score reply.
    try {
      const keepers = await prisma.scoreSubmission.findMany({
        where: { visitorId },
        orderBy: { createdAt: "desc" },
        take: MAX_HISTORY_PER_VISITOR,
        select: { id: true },
      });
      await prisma.scoreSubmission.deleteMany({
        where: {
          visitorId,
          id: { notIn: keepers.map((k) => k.id) },
        },
      });
    } catch (err) {
      console.error("history prune failed", err);
    }

    return NextResponse.json({
      type: "result",
      id: submission.id,
      score: agentResponse.score,
      band: agentResponse.band,
      recommendations: agentResponse.recommendations,
      message: agentResponse.message,
      previous_score: previous?.score ?? null,
      created_at: submission.createdAt.toISOString(),
    });
  } catch (err) {
    // DEBUG: expose the underlying error message so we can diagnose the
    // current Vercel deploy failure. Restore toEnvelope("INTERNAL_ERROR", 500)
    // before considering this production-ready.
    console.error("/api/checks failed:", err);
    const detail = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
    return NextResponse.json(
      { code: "INTERNAL_ERROR", message: `[debug] ${detail}` },
      { status: 500 },
    );
  }
}
