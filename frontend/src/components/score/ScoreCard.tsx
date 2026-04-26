"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { Band, Recommendation } from "@/lib/agent-client";

interface ScoreCardProps {
  score: number;
  band: Band;
  recommendations: Recommendation[];
  message: string;
  previousScore: number | null;
}

const BAND_COPY: Record<Band, string> = {
  HEALTHY: "Healthy",
  OKAY: "Okay",
  CRITICAL: "Needs attention",
};

const BAND_RING: Record<Band, string> = {
  HEALTHY: "border-band-healthy",
  OKAY: "border-band-okay",
  CRITICAL: "border-band-critical",
};

const BAND_FILL: Record<Band, string> = {
  HEALTHY: "bg-band-healthy",
  OKAY: "bg-band-okay",
  CRITICAL: "bg-band-critical",
};

const BAND_TEXT: Record<Band, string> = {
  HEALTHY: "text-band-healthy",
  OKAY: "text-band-okay",
  CRITICAL: "text-band-critical",
};

/**
 * Build the small progress / decline acknowledgement line shown beneath the
 * card when the visitor has run a check before.
 *
 * @param score - The visitor's freshly computed score.
 * @param previousScore - The most recent prior score, or null if this is
 *   their first session.
 * @param topRecommendation - The first item of {@link ScoreCardProps.recommendations}.
 * @returns A short, encouraging sentence, or null if no comparison is possible.
 */
function buildProgressLine(
  score: number,
  previousScore: number | null,
  topRecommendation: Recommendation | undefined,
): string | null {
  if (previousScore === null) return null;
  const delta = score - previousScore;
  if (delta > 0) return `+${delta} points since last time — nice momentum.`;
  if (delta < 0)
    return topRecommendation
      ? `Your next step: ${topRecommendation.title}`
      : "Every check is a step in the right direction.";
  return "Holding steady — try one small change before next time.";
}

/**
 * Render the score card with the band color, the agent's encouraging
 * message, and the prioritized fix list. Uses shadcn `Card` + `Progress`
 * (Constitution VI).
 *
 * @param props - {@link ScoreCardProps}.
 * @returns The card element.
 */
export function ScoreCard({
  score,
  band,
  recommendations,
  message,
  previousScore,
}: ScoreCardProps) {
  const progressLine = buildProgressLine(score, previousScore, recommendations[0]);

  return (
    <Card
      data-testid="score-card"
      data-band={band}
      className={cn("border-2", BAND_RING[band])}
    >
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle>Your password health</CardTitle>
          <span className={cn("text-sm font-medium uppercase", BAND_TEXT[band])}>
            {BAND_COPY[band]}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-end justify-between">
            <span className={cn("text-5xl font-semibold tabular-nums", BAND_TEXT[band])}>
              {score}
            </span>
            <span className="text-sm text-zinc-500">/ 100</span>
          </div>
          <Progress value={score} indicatorClassName={BAND_FILL[band]} />
        </div>

        <p className="text-sm text-zinc-700">{message}</p>

        {progressLine && (
          <p data-testid="progress-line" className="text-sm font-medium text-zinc-800">
            {progressLine}
          </p>
        )}

        {recommendations.length > 0 && (
          <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-800">
            {recommendations.map((r) => (
              <li key={r.id}>{r.title}</li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
