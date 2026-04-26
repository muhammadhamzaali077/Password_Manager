import { z } from "zod";

/**
 * Zod schema for a single chat message between the user and the agent.
 *
 * The Pydantic model on the agent side validates the same shape; this
 * client-side check protects the agent (Constitution III) from getting
 * called with malformed input.
 */
export const ChatMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(2_000),
});

/**
 * Zod schema for the inbound `POST /api/checks` body.
 *
 * Mirrors the agent's `ChatRequest` Pydantic model.
 */
export const ChatRequestSchema = z.object({
  messages: z.array(ChatMessageSchema).min(1).max(20),
});

export type ChatMessageInput = z.infer<typeof ChatMessageSchema>;
export type ChatRequestInput = z.infer<typeof ChatRequestSchema>;
