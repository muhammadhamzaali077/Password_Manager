import * as React from "react";

import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost";
}

/**
 * Button primitive matching the shadcn/ui surface area we use.
 *
 * @param props - Standard button props plus an optional `variant`.
 * @returns A styled `<button>` element.
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const base =
      "inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50";
    const styles =
      variant === "outline"
        ? "border border-zinc-300 bg-transparent hover:bg-zinc-100"
        : variant === "ghost"
          ? "hover:bg-zinc-100"
          : "bg-zinc-900 text-zinc-50 hover:bg-zinc-800";
    return <button ref={ref} className={cn(base, styles, className)} {...props} />;
  },
);
Button.displayName = "Button";

export { Button };
