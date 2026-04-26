import { z } from "zod";

/**
 * Zod schema mirroring `contracts/bff-checks.schema.json#/PostChecksRequest`.
 *
 * Constitution III: backend (Pydantic) is authoritative; this client check
 * is a fast feedback layer so we don't waste an LLM round-trip on garbage.
 */
export const PostChecksRequestSchema = z.object({
  password_count: z.number().int().min(0).max(10_000),
  oldest_password_age_months: z.number().int().min(0).max(600),
});

export type PostChecksRequest = z.infer<typeof PostChecksRequestSchema>;

/**
 * Parse and validate an incoming `POST /api/checks` payload.
 *
 * @param input - The raw, untrusted JSON body.
 * @returns A parsed, validated {@link PostChecksRequest}.
 * @throws ZodError when the input fails schema validation.
 */
export function parsePostChecksRequest(input: unknown): PostChecksRequest {
  return PostChecksRequestSchema.parse(input);
}

/**
 * Convert natural-language oldest-password age (e.g. "6 months", "3 years")
 * into an integer count of months.
 *
 * @param raw - Free-form age string from the chat input.
 * @returns Months as a non-negative integer, or null if the input cannot be
 *   parsed into a confident value.
 */
export function parseOldestAgeToMonths(raw: string): number | null {
  const trimmed = raw.trim().toLowerCase();
  if (!trimmed) return null;

  const numberMatch = trimmed.match(/^([0-9]+(?:\.[0-9]+)?)/);
  if (!numberMatch?.[1]) return null;
  const value = Number.parseFloat(numberMatch[1]);
  if (!Number.isFinite(value) || value < 0) return null;

  if (/(year|yr)/.test(trimmed)) return Math.round(value * 12);
  if (/(month|mo\b)/.test(trimmed)) return Math.round(value);
  if (/(week|wk)/.test(trimmed)) return Math.round(value / 4);
  if (/(day|d\b)/.test(trimmed)) return Math.round(value / 30);

  // Bare number → assume months (the most common answer for "how old?").
  return Math.round(value);
}

/**
 * Parse a free-form password-count answer into a non-negative integer.
 *
 * @param raw - Free-form count string from the chat input.
 * @returns A non-negative integer, or null if the input cannot be parsed.
 */
export function parsePasswordCount(raw: string): number | null {
  const match = raw.trim().match(/(-?[0-9]+)/);
  if (!match?.[1]) return null;
  const value = Number.parseInt(match[1], 10);
  if (!Number.isFinite(value) || value < 0) return null;
  return value;
}
