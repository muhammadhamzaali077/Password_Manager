export type Band = "HEALTHY" | "OKAY" | "CRITICAL";

export interface Recommendation {
  id: string;
  title: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
}

/**
 * The Python agent returns one of two shapes per turn — either a chat
 * message that continues the conversation, or a `result` once the
 * deterministic score has been computed.
 */
export type ChatTurnResponse =
  | { type: "message"; content: string }
  | {
      type: "result";
      score: number;
      band: Band;
      recommendations: Recommendation[];
      message: string;
      password_count: number;
      oldest_password_age_months: number;
    };

export interface AgentEnvelopeError {
  code:
    | "INVALID_INPUT"
    | "AGENT_TIMEOUT"
    | "AGENT_FORMAT_ERROR"
    | "RATE_LIMITED"
    | "INTERNAL_ERROR";
  message: string;
}

const AGENT_REQUEST_TIMEOUT_MS = 25_000;

/**
 * Resolve the agent URL.
 *
 * - `AGENT_URL` (set in local dev or for an externally-hosted agent) wins.
 * - On Vercel we fall back to the same deployment via `VERCEL_URL`.
 * - Otherwise default to the local FastAPI dev server on `:8765`.
 *
 * @returns The absolute URL to POST the chat request to.
 */
function resolveAgentUrl(): string {
  if (process.env.AGENT_URL) {
    return `${process.env.AGENT_URL.replace(/\/+$/, "")}/api/score`;
  }
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}/api/score`;
  }
  return "http://127.0.0.1:8765/api/score";
}

/**
 * Send the running chat history to the Python agent and parse the reply.
 *
 * @param payload - The chat request body (`{ messages }`).
 * @returns A typed {@link ChatTurnResponse} on success.
 * @throws An object matching {@link AgentEnvelopeError} on non-2xx, or a
 *   timeout / generic envelope on transport failure.
 */
export async function requestChat(payload: ChatRequest): Promise<ChatTurnResponse> {
  const url = resolveAgentUrl();
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
      | ChatTurnResponse
      | AgentEnvelopeError
      | null;

    if (!response.ok) {
      if (body && "code" in body) throw body;
      throw {
        code: "INTERNAL_ERROR",
        message: "Upstream returned no body.",
      } satisfies AgentEnvelopeError;
    }

    if (
      !body ||
      ((body as ChatTurnResponse).type !== "message" &&
        (body as ChatTurnResponse).type !== "result")
    ) {
      throw {
        code: "AGENT_FORMAT_ERROR",
        message: "Upstream returned a body that didn't match the contract.",
      } satisfies AgentEnvelopeError;
    }

    return body as ChatTurnResponse;
  } catch (err) {
    if (err && typeof err === "object" && "code" in err) throw err;
    if ((err as Error)?.name === "AbortError") {
      throw {
        code: "AGENT_TIMEOUT",
        message: "Upstream timed out.",
      } satisfies AgentEnvelopeError;
    }
    throw {
      code: "INTERNAL_ERROR",
      message: "Upstream request failed.",
    } satisfies AgentEnvelopeError;
  } finally {
    clearTimeout(timer);
  }
}
