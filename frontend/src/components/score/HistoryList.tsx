"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Band } from "@/lib/agent-client";

export interface HistoryEntry {
  id: string;
  score: number;
  band: Band;
  created_at: string;
}

interface HistoryListProps {
  entries: HistoryEntry[];
}

const DOT: Record<Band, string> = {
  HEALTHY: "bg-band-healthy",
  OKAY: "bg-band-okay",
  CRITICAL: "bg-band-critical",
};

/**
 * Format an ISO date as a short localized label (e.g. "Apr 26").
 *
 * @param iso - ISO-8601 string from the server.
 * @returns A short user-facing label.
 */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * Render the visitor's past scores newest-first. When there is no history,
 * shows an encouraging first-time message instead of an empty grid (FR-012).
 *
 * @param props - {@link HistoryListProps}.
 * @returns A history card.
 */
export function HistoryList({ entries }: HistoryListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Your check-ins</CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-zinc-600">
            This is your first check — there's nowhere to go but up. Come back
            any time and we'll track your progress here.
          </p>
        ) : (
          <ul className="space-y-2">
            {entries.map((entry) => (
              <li
                key={entry.id}
                className="flex items-center justify-between text-sm"
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className={cn("inline-block h-2.5 w-2.5 rounded-full", DOT[entry.band])}
                  />
                  <span className="tabular-nums font-medium">{entry.score}</span>
                  <span className="text-zinc-500">/ 100</span>
                </span>
                <span className="text-zinc-500">{formatDate(entry.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
