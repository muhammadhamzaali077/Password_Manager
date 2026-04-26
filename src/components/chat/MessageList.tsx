"use client";

import { cn } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  author: "agent" | "user" | "system-error";
  text: string;
}

interface MessageListProps {
  messages: ChatMessage[];
}

/**
 * Render a vertically stacked chat transcript. The visual treatment is
 * minimal so it stays readable at a 375 px viewport (Constitution V).
 *
 * @param props - {@link MessageListProps}.
 * @returns A `<div>` containing one bubble per message.
 */
export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-3">
      {messages.map((m) => (
        <div
          key={m.id}
          data-testid={`msg-${m.author}`}
          className={cn(
            "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed",
            m.author === "agent" && "bg-zinc-100 text-zinc-800",
            m.author === "user" &&
              "ml-auto bg-zinc-900 text-zinc-50",
            m.author === "system-error" &&
              "bg-amber-50 text-amber-900 border border-amber-200",
          )}
        >
          {m.text}
        </div>
      ))}
    </div>
  );
}
