export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  organization: {
    id: string;
    name: string;
    slug: string;
  } | null;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface Citation {
  index: number;
  source: "slack" | "gdrive" | "gmail" | "notion";
  title: string;
  author_name: string;
  author_email: string;
  created_at: string;
  source_url: string;
  source_item_id: string;
  excerpt: string;
  source_metadata: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Citation[];
  created_at: string;
}

export interface Thread {
  id: string;
  title: string;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ThreadDetail extends Thread {
  messages: Message[];
}

export interface Integration {
  id: string;
  source: "slack" | "gdrive" | "gmail" | "notion";
  source_display: string;
  display_name: string;
  is_active: boolean;
  last_synced_at: string | null;
  created_at: string;
}

export interface SyncLog {
  id: string;
  integration: string;
  integration_source: string;
  started_at: string;
  completed_at: string | null;
  status: "running" | "success" | "failed" | "partial";
  docs_processed: number;
  docs_failed: number;
  error_message: string | null;
  triggered_by: "scheduled" | "webhook" | "manual";
}

// SSE stream event types
export type StreamEvent =
  | { type: "delta"; content: string }
  | { type: "sources"; sources: Citation[] }
  | { type: "done" }
  | { type: "error"; message: string };
