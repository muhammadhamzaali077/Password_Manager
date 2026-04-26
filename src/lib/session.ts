import { cookies } from "next/headers";
import { randomBytes } from "node:crypto";

import { prisma } from "@/lib/prisma";

const COOKIE_NAME = process.env.SESSION_COOKIE_NAME ?? "pmh_session";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365; // 1 year (research §R3)

/**
 * Generate a 128-bit URL-safe random token for the session cookie.
 *
 * @returns A 22+ character base64url string with no padding.
 */
function newSessionToken(): string {
  return randomBytes(16).toString("base64url");
}

/**
 * Read the visitor's session cookie if one is set, otherwise mint a new one.
 *
 * The cookie is `HttpOnly`, `Secure`, and `SameSite=Lax` per research §R3.
 * On first visit, this function also creates the matching `Visitor` row so
 * later inserts can reference it via foreign key.
 *
 * @returns The Visitor's database id and session token.
 */
export async function getOrCreateVisitor(): Promise<{
  visitorId: string;
  sessionToken: string;
  isNew: boolean;
}> {
  const jar = await cookies();
  const existing = jar.get(COOKIE_NAME)?.value;

  if (existing) {
    const visitor = await prisma.visitor.findUnique({
      where: { sessionToken: existing },
    });
    if (visitor) {
      // Touch lastSeenAt without awaiting heavily — fire-and-forget is fine.
      prisma.visitor
        .update({
          where: { id: visitor.id },
          data: { lastSeenAt: new Date() },
        })
        .catch(() => undefined);
      return { visitorId: visitor.id, sessionToken: visitor.sessionToken, isNew: false };
    }
    // Cookie is set but no row exists (e.g. DB was reset); mint a new one.
  }

  const token = newSessionToken();
  const visitor = await prisma.visitor.create({
    data: { sessionToken: token },
  });

  jar.set({
    name: COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_SECONDS,
  });

  return { visitorId: visitor.id, sessionToken: token, isNew: true };
}

/**
 * Look up the current visitor from the cookie without creating one.
 *
 * @returns The Visitor's database id, or null if no valid cookie is present.
 */
export async function getVisitorOrNull(): Promise<{ visitorId: string } | null> {
  const jar = await cookies();
  const token = jar.get(COOKIE_NAME)?.value;
  if (!token) return null;

  const visitor = await prisma.visitor.findUnique({
    where: { sessionToken: token },
    select: { id: true },
  });
  return visitor ? { visitorId: visitor.id } : null;
}
