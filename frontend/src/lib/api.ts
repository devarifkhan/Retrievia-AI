import axios, { AxiosInstance } from "axios";
import type {
  AuthTokens,
  Integration,
  Message,
  SyncLog,
  Thread,
  ThreadDetail,
  User,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${API_URL}/api`,
    headers: { "Content-Type": "application/json" },
  });

  // Attach JWT access token to every request
  client.interceptors.request.use((config) => {
    const tokens = getStoredTokens();
    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    return config;
  });

  // Auto-refresh on 401
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        try {
          const tokens = getStoredTokens();
          if (!tokens?.refresh) throw new Error("No refresh token");
          const { data } = await axios.post(`${API_URL}/api/auth/refresh/`, {
            refresh: tokens.refresh,
          });
          storeTokens({ access: data.access, refresh: tokens.refresh });
          original.headers.Authorization = `Bearer ${data.access}`;
          return client(original);
        } catch {
          clearTokens();
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const api = createApiClient();

// ── Token Storage ──────────────────────────────────────────────────────────

export function getStoredTokens(): AuthTokens | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("retrievia_tokens");
  return raw ? JSON.parse(raw) : null;
}

export function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem("retrievia_tokens", JSON.stringify(tokens));
}

export function clearTokens(): void {
  localStorage.removeItem("retrievia_tokens");
  localStorage.removeItem("retrievia_user");
}

// ── Auth ──────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (email: string, password: string): Promise<{ user: User } & AuthTokens> => {
    const { data } = await api.post("/auth/login/", { email, password });
    return data;
  },
  logout: async (refresh: string): Promise<void> => {
    await api.post("/auth/logout/", { refresh });
  },
};

// ── Threads ───────────────────────────────────────────────────────────────

export const chatApi = {
  listThreads: async (): Promise<Thread[]> => {
    const { data } = await api.get("/chat/threads/");
    return data.results ?? data;
  },
  createThread: async (): Promise<Thread> => {
    const { data } = await api.post("/chat/threads/", {});
    return data;
  },
  getThread: async (id: string): Promise<ThreadDetail> => {
    const { data } = await api.get(`/chat/threads/${id}/`);
    return data;
  },
  deleteThread: async (id: string): Promise<void> => {
    await api.delete(`/chat/threads/${id}/`);
  },
  listMessages: async (threadId: string): Promise<Message[]> => {
    const { data } = await api.get(`/chat/threads/${threadId}/messages/`);
    return data;
  },
};

// ── Integrations ──────────────────────────────────────────────────────────

export const integrationApi = {
  list: async (): Promise<Integration[]> => {
    const { data } = await api.get("/integrations/");
    return data.results ?? data;
  },
  triggerSync: async (id: string): Promise<{ task_id: string }> => {
    const { data } = await api.post(`/integrations/${id}/sync/`);
    return data;
  },
  listSyncLogs: async (): Promise<SyncLog[]> => {
    const { data } = await api.get("/integrations/sync-logs/");
    return data.results ?? data;
  },
  getOAuthUrl: async (source: string): Promise<string> => {
    const { data } = await api.get(`/integrations/${source}/oauth/initiate/`);
    return data.oauth_url;
  },
};

// ── SSE Streaming ─────────────────────────────────────────────────────────

export function streamMessage(
  threadId: string,
  content: string,
  onDelta: (text: string) => void,
  onSources: (sources: unknown[]) => void,
  onDone: () => void,
  onError: (msg: string) => void
): () => void {
  const tokens = getStoredTokens();
  const controller = new AbortController();

  fetch(`${API_URL}/api/chat/threads/${threadId}/messages/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${tokens?.access || ""}`,
    },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      onError(`HTTP ${response.status}`);
      return;
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        try {
          const event = JSON.parse(raw);
          if (event.type === "delta") onDelta(event.content);
          else if (event.type === "sources") onSources(event.sources);
          else if (event.type === "done") onDone();
          else if (event.type === "error") onError(event.message);
        } catch {
          // ignore parse errors
        }
      }
    }
  }).catch((err) => {
    if (err.name !== "AbortError") onError(String(err));
  });

  return () => controller.abort();
}
