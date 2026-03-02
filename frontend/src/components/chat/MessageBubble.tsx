"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types";
import { SourceCard } from "./SourceCard";

interface Props {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? "order-2" : "order-1"}`}>
        {/* Avatar */}
        <div className={`flex items-end gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
              isUser ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
            }`}
          >
            {isUser ? "U" : "R"}
          </div>

          <div
            className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
              isUser
                ? "bg-brand-600 text-white rounded-br-sm"
                : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
            }`}
          >
            {isUser ? (
              <p>{message.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none prose-gray">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
                {isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-gray-400 ml-0.5 animate-cursor-blink" />
                )}
              </div>
            )}
          </div>
        </div>

        {/* Source cards below assistant message */}
        {!isUser && message.sources && message.sources.length > 0 && !isStreaming && (
          <div className="mt-2 ml-9 space-y-1.5">
            <p className="text-xs text-gray-400 font-medium mb-1">Sources</p>
            {message.sources.map((citation) => (
              <SourceCard key={citation.index} citation={citation} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
