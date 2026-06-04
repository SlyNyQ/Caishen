import type { ChatResponse } from "@/lib/types";

type InsightsPanelProps = {
  response: ChatResponse | null;
};

function formatPrice(value: number | null | undefined, currency?: string | null): string {
  if (value == null) {
    return "Unavailable";
  }
  return `${currency || ""} ${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`.trim();
}

export function InsightsPanel({ response }: InsightsPanelProps) {
  const analysis = response?.analysis;
  return (
    <aside className="insights-panel" aria-label="Research insights">
      <div className="panel-heading">
        <p className="section-kicker">Research brief</p>
        <h2>Evidence at a glance</h2>
      </div>

      {analysis?.market_snapshots.length ? (
        <section className="insight-section">
          <h3>Market snapshots</h3>
          <div className="snapshot-grid">
            {analysis.market_snapshots.map((snapshot) => (
              <article className="snapshot-card" key={snapshot.ticker}>
                <div className="snapshot-title">
                  <strong>{snapshot.ticker}</strong>
                  <span className={`data-status ${snapshot.status}`}>{snapshot.status}</span>
                </div>
                <p>{snapshot.company_name}</p>
                <div className="snapshot-price">{formatPrice(snapshot.current_price, snapshot.currency)}</div>
                {snapshot.percent_change != null ? (
                  <span className={snapshot.percent_change >= 0 ? "positive" : "negative"}>
                    {snapshot.percent_change >= 0 ? "+" : ""}
                    {snapshot.percent_change.toFixed(2)}% today
                  </span>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : (
        <div className="empty-insights">
          <span>01</span>
          <p>Add a ticker or public source, then ask a question to build a research brief.</p>
        </div>
      )}

      {analysis?.key_takeaways.length ? (
        <section className="insight-section">
          <h3>Key takeaways</h3>
          <ul>{analysis.key_takeaways.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      ) : null}

      {analysis?.risk_notes.length ? (
        <section className="insight-section risk-section">
          <h3>Risk notes</h3>
          <ul>{analysis.risk_notes.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      ) : null}

      {response?.citations.length ? (
        <section className="insight-section">
          <h3>Sources</h3>
          {response.citations.map((citation) => (
            <article className="source-card" key={citation.doc_id}>
              <strong>{citation.title}</strong>
              <p>{citation.snippet}</p>
            </article>
          ))}
        </section>
      ) : null}
    </aside>
  );
}
