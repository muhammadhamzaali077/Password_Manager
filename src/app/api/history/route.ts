import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { getVisitorOrNull } from "@/lib/session";

const MAX_HISTORY_PER_VISITOR = 50;

/**
 * `GET /api/history` — return up to the 50 most recent submissions for the
 * visitor identified by the session cookie. If there is no cookie or no
 * matching visitor, returns `{ history: [] }` so the UI shows the friendly
 * empty state (FR-012) instead of an error.
 *
 * @returns A JSON response conforming to
 *   `contracts/bff-checks.schema.json#/definitions/GetHistoryResponse`.
 */
export async function GET() {
  const visitor = await getVisitorOrNull();
  if (!visitor) return NextResponse.json({ history: [] });

  const rows = await prisma.scoreSubmission.findMany({
    where: { visitorId: visitor.visitorId },
    orderBy: { createdAt: "desc" },
    take: MAX_HISTORY_PER_VISITOR,
    select: { id: true, score: true, band: true, createdAt: true },
  });

  return NextResponse.json({
    history: rows.map((r) => ({
      id: r.id,
      score: r.score,
      band: r.band,
      created_at: r.createdAt.toISOString(),
    })),
  });
}
