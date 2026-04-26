import { ChatPane } from "@/components/chat/ChatPane";

/**
 * Home page — the only screen this product has. Renders the chat surface
 * inside a centered, mobile-first column.
 */
export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-svh max-w-xl flex-col gap-6 px-4 py-6 sm:py-10">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Password Manager Health Check
        </h1>
        <p className="text-sm text-zinc-600">
          Two quick questions, one friendly score.
        </p>
      </header>
      <ChatPane />
    </main>
  );
}
