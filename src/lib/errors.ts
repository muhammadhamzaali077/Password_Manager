import { NextResponse } from "next/server";

/**
 * Stable error codes shared across the whole product (Constitution VII).
 * The chat surface only ever renders the matching `message` string —
 * never the code, never raw exception content (Constitution IV).
 */
export type ErrorCode =
  | "INVALID_INPUT"
  | "AGENT_TIMEOUT"
  | "AGENT_FORMAT_ERROR"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR";

const FRIENDLY_MESSAGES: Record<ErrorCode, string> = {
  INVALID_INPUT: "I didn't quite catch that — could you give me a number?",
  AGENT_TIMEOUT: "That took longer than expected. Want to try once more?",
  AGENT_FORMAT_ERROR: "I had trouble putting that together. Mind sending it again?",
  RATE_LIMITED: "You're moving fast! Give it a moment and try again.",
  INTERNAL_ERROR: "Something hiccuped on our side. Please try again in a bit.",
};

/**
 * Map a stable error code to its user-safe sentence.
 *
 * @param code - One of the reserved {@link ErrorCode} values.
 * @returns A short, encouraging sentence safe to render directly in the UI.
 */
export function friendlyMessageFor(code: ErrorCode): string {
  return FRIENDLY_MESSAGES[code] ?? FRIENDLY_MESSAGES.INTERNAL_ERROR;
}

/**
 * Build a NextResponse following the universal error envelope.
 *
 * @param code - One of the reserved error codes.
 * @param status - HTTP status code (4xx for client errors, 5xx otherwise).
 * @param message - Optional override for the user-facing text.
 * @returns A NextResponse whose body is exactly `{ code, message }`.
 */
export function toEnvelope(
  code: ErrorCode,
  status: number,
  message?: string,
): NextResponse {
  return NextResponse.json(
    { code, message: message ?? friendlyMessageFor(code) },
    { status },
  );
}
