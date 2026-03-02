"use client";
import { useState } from "react";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import type { Citation } from "@/types";
import { format } from "date-fns";

const SOURCE_ICONS: Record<string, string> = {
  slack: "💬",
  gdrive: "📄",
  notion: "📝",
  gmail: "✉️",
};

export function SourceCard({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);

  const date = citation.created_at
    ? format(new Date(citation.created_at), "MMM d, yyyy")
    : "Unknown date";

  const icon = SOURCE_ICONS[citation.source] || "📎";

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden text-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 text-left transition-colors"
      >
        <span className="text-base">{icon}</span>
        <div className="flex-1 min-w-0">
          <span className="font-medium text-gray-800 truncate block">{citation.title}</span>
          <span className="text-xs text-gray-500">
            {citation.author_name} · {date}
          </span>
        </div>
        <span className="text-xs text-brand-600 font-medium shrink-0">
          Source {citation.index}
        </span>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-3 py-2 bg-white border-t border-gray-100">
          <p className="text-gray-600 text-xs leading-relaxed mb-2">{citation.excerpt}</p>
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              Open original
            </a>
          )}
        </div>
      )}
    </div>
  );
}
