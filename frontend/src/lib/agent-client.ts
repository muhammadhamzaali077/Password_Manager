import type { PostChecksRequest } from "@/lib/validation";

export type Band = "HEALTHY" | "OKAY" | "CRITICAL";

export interface Recommendation {
  id: string;
  title: string;
}

export interface AgentScoreResponse {
  score: number;
  band: Band;
  recommendations: Recommendation[];
  message: string;
}

export interface AgentEnvelopeError {
  code:
    | "INVALID_INPUT"
    | "AGENT_TIMEOUT"
    | "AGENT_FORMAT_ERROR"
    | "RATE_LIMITED"
    | "INTERNAL_ERROR";
  message: string;
}

const AGENT_REQUEST_TIMEOUT_MS = 18_000;

/**
 * Call the FastAPI agent's `POST /agent/score` endpoint.
 *
 * @param payload - The validated request body.
 * @returns The parsed structured-JSON response on success.
 * @throws An object matching {@link AgentEnvelopeError} when the upstream
 *   returns a non-2xx; throws a generic Error on transport failure.
 */
export async function requestScore(
  payload: PostChecksRequest,
): Promise<AgentScoreResponse> {
  const baseUrl = process.env.AGENT_URL ?? "http://127.0.0.1:8000";
  const url = `${baseUrl.replace(/\/+$/, "")}/agent/score`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), AGENT_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: "no-store",
    });

    const body = (await response.json().catch(() => null)) as
      | AgentScoreResponse
      | AgentEnvelopeError
      | null;

    if (!response.ok) {
      if (body && "code" in body) throw body;
      throw { code: "INTERNAL_ERROR", message: "Upstream returned no body." } satisfies AgentEnvelopeError;
    }

    if (
      !body ||
      typeof (body as AgentScoreResponse).score !== "number" ||
      typeof (body as AgentScoreResponse).band !== "string" ||
      !Array.isArray((body as AgentScoreResponse).recommendations)
    ) {
      throw {
        code: "AGENT_FORMAT_ERROR",
        message: "Upstream returned a body that didn't match the contract.",
      } satisfies AgentEnvelopeError;
    }

    return body as AgentScoreResponse;
  } catch (err) {
    if (err && typeof err === "object" && "code" in err) throw err;
    if ((err as Error)?.name === "AbortError") {
      throw { code: "AGENT_TIMEOUT", message: "Upstream timed out." } satisfies AgentEnvelopeError;
    }
    throw { code: "INTERNAL_ERROR", message: "Upstream request failed." } satisfies AgentEnvelopeError;
  } finally {
    clearTimeout(timer);
  }
}
