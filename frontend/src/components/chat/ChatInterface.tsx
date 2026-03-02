"use client";
import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import toast from "react-hot-toast";
import type { Citation, Message } from "@/types";
import { chatApi, streamMessage } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";

interface Props {
  threadId: string;
}

export function ChatInterface({ threadId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingSources, setStreamingSources] = useState<Citation[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);
  // Refs mirror state so async callbacks always read the latest value (avoids stale closure)
  const streamingContentRef = useRef("");
  const streamingSourcesRef = useRef<Citation[]>([]);

  useEffect(() => {
    chatApi.listMessages(threadId).then((msgs) => {
      setMessages(msgs);
      setLoading(false);
    });
    return () => abortRef.current?.();
  }, [threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const send = async () => {
    const content = input.trim();
    if (!content || streaming) return;

    // M2: Abort any in-flight stream before starting a new one
    abortRef.current?.();

    setInput("");

    // Optimistically add user message
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamingContent("");
    setStreamingSources([]);
    // C1: Reset refs so the onDone callback reads fresh values
    streamingContentRef.current = "";
    streamingSourcesRef.current = [];

    abortRef.current = streamMessage(
      threadId,
      content,
      (delta) => {
        streamingContentRef.current += delta;
        setStreamingContent((prev) => prev + delta);
      },
      (sources) => {
        streamingSourcesRef.current = sources as Citation[];
        setStreamingSources(sources as Citation[]);
      },
      () => {
        // C1: Read from refs — they always hold the final accumulated values
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: streamingContentRef.current,
            sources: streamingSourcesRef.current,
            created_at: new Date().toISOString(),
          },
        ]);
        setStreamingContent("");
        setStreamingSources([]);
        setStreaming(false);
      },
      (error) => {
        toast.error(`Error: ${error}`);
        setStreaming(false);
        setStreamingContent("");
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !streaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-3">🔍</div>
            <h3 className="text-lg font-semibold text-gray-700">Ask anything</h3>
            <p className="text-sm text-gray-400 mt-1 max-w-xs">
              Search across Slack, Google Drive, Notion, and Gmail — all in one place.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {streaming && streamingContent && (
          <MessageBubble
            message={{
              id: "streaming",
              role: "assistant",
              content: streamingContent,
              sources: [],
              created_at: new Date().toISOString(),
            }}
            isStreaming
          />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 px-4 py-3 bg-white">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question across all your sources..."
            rows={1}
            className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 max-h-32 overflow-y-auto"
            style={{ height: "auto" }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "auto";
              target.style.height = Math.min(target.scrollHeight, 128) + "px";
            }}
          />
          <button
            onClick={send}
            disabled={streaming || !input.trim()}
            className="bg-brand-600 text-white p-2.5 rounded-xl hover:bg-brand-700 disabled:opacity-40 transition-colors shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-1.5">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
