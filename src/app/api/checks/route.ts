import { Prisma } from "@prisma/client";
import { NextResponse, type NextRequest } from "next/server";

import { requestScore } from "@/lib/agent-client";
import { toEnvelope } from "@/lib/errors";
import { prisma } from "@/lib/prisma";
import { getOrCreateVisitor } from "@/lib/session";
import { PostChecksRequestSchema } from "@/lib/validation";

const MAX_HISTORY_PER_VISITOR = 50;

/**
 * `POST /api/checks` — accept the validated chat answers, ask the agent for
 * a structured score, persist it for the visitor, and return the BFF
 * response shape defined in `contracts/bff-checks.schema.json`.
 *
 * @param request - The incoming Next.js request. The body MUST conform to
 *   `PostChecksRequestSchema`.
 * @returns A JSON response: success body on 200, `{ code, message }` envelope
 *   on any failure.
 */
export async function POST(request: NextRequest) {
  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return toEnvelope("INVALID_INPUT", 400);
  }

  const parsed = PostChecksRequestSchema.safeParse(raw);
  if (!parsed.success) return toEnvelope("INVALID_INPUT", 400);

  const { visitorId } = await getOrCreateVisitor();

  // Fetch the most recent prior submission BEFORE inserting (US2: previous_score).
  const previous = await prisma.scoreSubmission.findFirst({
    where: { visitorId },
    orderBy: { createdAt: "desc" },
    select: { score: true },
  });

  let agentResponse;
  try {
    agentResponse = await requestScore(parsed.data);
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

  const submission = await prisma.scoreSubmission.create({
    data: {
      visitorId,
      passwordCount: parsed.data.password_count,
      oldestPasswordAgeMonths: parsed.data.oldest_password_age_months,
      score: agentResponse.score,
      band: agentResponse.band,
      recommendations: agentResponse.recommendations as unknown as Prisma.InputJsonValue,
    },
  });

  // Prune to the 50 newest submissions per visitor (research §R9).
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

  return NextResponse.json({
    id: submission.id,
    score: agentResponse.score,
    band: agentResponse.band,
    recommendations: agentResponse.recommendations,
    message: agentResponse.message,
    previous_score: previous?.score ?? null,
    created_at: submission.createdAt.toISOString(),
  });
}
