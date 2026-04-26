import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ScoreCard } from "@/components/score/ScoreCard";

describe("<ScoreCard>", () => {
  it("renders the score, band label, and recommendation list", () => {
    render(
      <ScoreCard
        score={72}
        band="OKAY"
        recommendations={[
          { id: "ENABLE_MFA_EVERYWHERE", title: "Turn on two-factor wherever it's offered." },
          { id: "REMOVE_REUSED_PASSWORDS", title: "Find any reused passwords and give each their own." },
        ]}
        message="Solid foundation — one rotation will push you into the green."
        previousScore={null}
      />,
    );

    expect(screen.getByTestId("score-card")).toHaveAttribute("data-band", "OKAY");
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText("Okay")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("applies the band ring class for the CRITICAL band", () => {
    render(
      <ScoreCard
        score={32}
        band="CRITICAL"
        recommendations={[]}
        message="One small step today."
        previousScore={null}
      />,
    );
    expect(screen.getByTestId("score-card")).toHaveClass("border-band-critical");
  });

  it("acknowledges improvement when previousScore is lower", () => {
    render(
      <ScoreCard
        score={84}
        band="HEALTHY"
        recommendations={[
          { id: "CELEBRATE_HEALTHY", title: "Keep up the routine." },
        ]}
        message="You're moving up."
        previousScore={70}
      />,
    );
    expect(screen.getByTestId("progress-line").textContent).toMatch(/\+14 points/);
  });

  it("shows a next-step framing when previousScore is higher", () => {
    render(
      <ScoreCard
        score={60}
        band="OKAY"
        recommendations={[
          { id: "ROTATE_OLDEST_PASSWORD", title: "Replace your oldest password." },
        ]}
        message="Small step today."
        previousScore={75}
      />,
    );
    expect(screen.getByTestId("progress-line").textContent).toMatch(/Replace your oldest password/);
  });
});
