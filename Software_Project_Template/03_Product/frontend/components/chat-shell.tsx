"use client";

import { useEffect, useRef, useState } from "react";

import { ContextBar } from "@/components/context-bar";
import { InsightsPanel } from "@/components/insights-panel";
import { MessageInput } from "@/components/message-input";
import { MessageList } from "@/components/message-list";
import { getHealth, sendChat } from "@/lib/api";
import type {
  AnalysisContext,
  ChatResponse,
  ConversationMessage,
  HealthResponse,
  ProviderName
} from "@/lib/types";

type ChatShellProps = {
  showDebug?: boolean;
};

const initialContext: AnalysisContext = {
  tickers: [],
  source_urls: [],
  risk_tolerance: "unspecified",
  horizon: "unspecified",
  goal: null
};

const quickPrompts = [
  "Compare AAPL and MSFT",
  "Explain volatility risk",
  "Build a long-term research checklist"
];

export function ChatShell({ showDebug = false }: ChatShellProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [context, setContext] = useState<AnalysisContext>(initialContext);
  const [provider, setProvider] = useState<ProviderName>("mock");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      id: "assistant-intro",
      role: "assistant",
      content:
        "Bring me a ticker, a public source, or an investment concept. I will separate evidence, uncertainty, and educational scenarios."
    }
  ]);

  useEffect(() => {
    getHealth()
      .then((response) => {
        setHealth(response);
        setHealthError(null);
      })
      .catch((error: Error) => setHealthError(error.message));
  }, []);

  useEffect(() => {
    if (!loading) {
      inputRef.current?.focus();
    }
  }, [loading]);

  const handleSubmit = async () => {
    const nextInput = input.trim();
    if (!nextInput || loading) {
      return;
    }
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", content: nextInput }
    ]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChat({
        message: nextInput,
        session_id: sessionId,
        provider,
        analysis_context: context
      });
      setSessionId(response.session_id);
      setLatestResponse(response);
      setMessages((current) => [
        ...current,
        {
          id: response.request_id,
          role: "assistant",
          content: response.answer,
          response
        }
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown analysis error.";
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `Analysis request failed: ${message}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="research-workspace" aria-label="Caishen investment research workspace">
      <aside className="workspace-nav">
        <div>
          <a className="wordmark" href="/" aria-label="Caishen home">
            <span className="wordmark-mark">C</span>
            <span>Caishen</span>
          </a>
          <p className="nav-caption">Investment research, translated.</p>
        </div>
        <nav aria-label="Workspace navigation">
          <a className="nav-item active" href="#research">Research</a>
          <a className="nav-item" href="#insights">Insights</a>
          <a className="nav-item" href="/debug">Debug</a>
        </nav>
        <label className="provider-control">
          <span>Analysis provider</span>
          <select
            aria-label="Analysis provider"
            value={provider}
            onChange={(event) => setProvider(event.target.value as ProviderName)}
          >
            <option value="mock">Mock / offline</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
            <option value="bedrock">AWS Bedrock</option>
          </select>
        </label>
        <div className="nav-disclaimer">
          <span>Read-only</span>
          <p>Educational analysis, never trade execution or guaranteed outcomes.</p>
        </div>
      </aside>

      <main className="research-main" id="research">
        <header className="research-header">
          <div>
            <p className="section-kicker">Research desk</p>
            <h1>Think through an investment.</h1>
            <p>Current market context, public-source evidence, and plain-English risk framing.</p>
          </div>
          <div className="health-chip" aria-live="polite">
            <span className={healthError ? "health-dot error" : "health-dot"} />
            <div>
              <strong>{healthError ? "Backend unavailable" : health?.status || "Checking"}</strong>
              <span>{healthError || health?.environment || "local"}</span>
            </div>
          </div>
        </header>

        <ContextBar context={context} onChange={setContext} />

        <div className="quick-prompts" aria-label="Suggested research prompts">
          {quickPrompts.map((prompt) => (
            <button key={prompt} type="button" onClick={() => setInput(prompt)}>
              {prompt}
            </button>
          ))}
        </div>

        <MessageList messages={messages} showDebug={showDebug} />
        <MessageInput
          ref={inputRef}
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={loading}
        />
      </main>

      <div id="insights">
        <InsightsPanel response={latestResponse} />
      </div>
    </section>
  );
}
