import { ChatShell } from "@/components/chat-shell";

export default function DebugPage() {
  return (
    <main className="page-shell">
      <p className="debug-note">
        Debug mode shows market-data traces, source retrieval, and provider metadata.
      </p>
      <ChatShell showDebug />
    </main>
  );
}
