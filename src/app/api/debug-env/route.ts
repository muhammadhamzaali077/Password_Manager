import { NextResponse } from "next/server";

/**
 * `GET /api/debug-env` — diagnostic endpoint that reports which env
 * vars Vercel actually injected into the running function. Returns
 * only booleans + non-sensitive identifiers — never the secret values.
 *
 * @returns A JSON snapshot of env-var presence.
 */
export async function GET() {
  return NextResponse.json({
    has_DATABASE_URL: Boolean(process.env.DATABASE_URL),
    has_OPENAI_API_KEY: Boolean(process.env.OPENAI_API_KEY),
    VERCEL_ENV: process.env.VERCEL_ENV ?? null,
    VERCEL_URL: process.env.VERCEL_URL ?? null,
    VERCEL_GIT_COMMIT_REF: process.env.VERCEL_GIT_COMMIT_REF ?? null,
    DATABASE_URL_first_char:
      typeof process.env.DATABASE_URL === "string"
        ? process.env.DATABASE_URL.charAt(0)
        : null,
  });
}
