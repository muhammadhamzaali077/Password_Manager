import { PrismaClient } from "@prisma/client";

declare global {
  // eslint-disable-next-line no-var
  var __prisma__: PrismaClient | undefined;
}

/**
 * Reusable Prisma client. We attach to globalThis in development so that
 * Next.js hot reload doesn't open a new pool on every request.
 */
export const prisma: PrismaClient =
  globalThis.__prisma__ ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["warn", "error"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") {
  globalThis.__prisma__ = prisma;
}
