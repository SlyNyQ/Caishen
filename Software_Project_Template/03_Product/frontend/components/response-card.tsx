import type { ChatResponse } from "@/lib/types";

type ResponseCardProps = {
  response: ChatResponse;
  showDebug?: boolean;
};

export function ResponseCard({ response, showDebug = false }: ResponseCardProps) {
  return (
    <div className="response-card">
      <div className="response-labels">
        <span>{response.route.replaceAll("_", " ")}</span>
        <span>{response.provider} | {response.model}</span>
      </div>
      <p className="response-answer">{response.answer}</p>

      {response.refusal ? (
        <div className="response-callout">
          <strong>Safety boundary</strong>
          <p>{response.refusal.message}</p>
        </div>
      ) : null}

      {response.analysis.strategy_scenarios.length ? (
        <div className="response-section">
          <strong>Educational scenarios</strong>
          <ul>
            {response.analysis.strategy_scenarios.slice(0, 3).map((scenario) => (
              <li key={scenario}>{scenario}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {showDebug && response.tool_traces.length ? (
        <details className="debug-details">
          <summary>Tool traces</summary>
          <pre>{JSON.stringify(response.tool_traces, null, 2)}</pre>
        </details>
      ) : null}
      {showDebug && Object.keys(response.debug).length ? (
        <details className="debug-details">
          <summary>Debug metadata</summary>
          <pre>{JSON.stringify(response.debug, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
