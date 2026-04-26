import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class names safely (shadcn/ui convention).
 *
 * @param inputs - Any mixture of strings, arrays, or conditionals accepted by clsx.
 * @returns A single deduplicated class-name string with later utilities winning.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
