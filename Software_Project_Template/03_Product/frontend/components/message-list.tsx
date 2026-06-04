import { ResponseCard } from "@/components/response-card";
import type { ConversationMessage } from "@/lib/types";

type MessageListProps = {
  messages: ConversationMessage[];
  showDebug?: boolean;
};

export function MessageList({ messages, showDebug = false }: MessageListProps) {
  return (
    <div className="message-list" aria-live="polite">
      {messages.map((message) => {
        const isUser = message.role === "user";
        return (
          <article key={message.id} className={isUser ? "message-row user" : "message-row assistant"}>
            <span className="message-meta">{isUser ? "You" : "Caishen"}</span>
            {isUser ? (
              <div className="message-bubble user-bubble">{message.content}</div>
            ) : message.response ? (
              <ResponseCard response={message.response} showDebug={showDebug} />
            ) : (
              <div className="message-bubble assistant-bubble">{message.content}</div>
            )}
          </article>
        );
      })}
    </div>
  );
}
