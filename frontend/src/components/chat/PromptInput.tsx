"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface PromptInputProps {
  placeholder: string;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

/**
 * Single-line chat input. Submitting on Enter or via the Send button forwards
 * the trimmed value to the parent and clears the field.
 *
 * @param props - {@link PromptInputProps}.
 * @returns A form element with an `<input>` and a Send button.
 */
export function PromptInput({ placeholder, onSubmit, disabled }: PromptInputProps) {
  const [value, setValue] = React.useState("");

  /**
   * Handle form submission: trim, forward to parent, clear.
   */
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        inputMode="text"
        autoFocus
      />
      <Button type="submit" disabled={disabled || !value.trim()}>
        Send
      </Button>
    </form>
  );
}
