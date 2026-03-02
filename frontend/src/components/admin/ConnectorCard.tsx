"use client";
import { useState } from "react";
import { RefreshCw, CheckCircle, XCircle, Clock, ExternalLink } from "lucide-react";
import toast from "react-hot-toast";
import type { Integration } from "@/types";
import { integrationApi } from "@/lib/api";
import { format } from "date-fns";

const SOURCE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  slack: { label: "Slack", icon: "💬", color: "bg-purple-50 border-purple-200" },
  gdrive: { label: "Google Drive", icon: "📄", color: "bg-blue-50 border-blue-200" },
  notion: { label: "Notion", icon: "📝", color: "bg-gray-50 border-gray-200" },
  gmail: { label: "Gmail", icon: "✉️", color: "bg-red-50 border-red-200" },
};

interface Props {
  integration: Integration;
  onSyncTriggered: () => void;
}

export function ConnectorCard({ integration, onSyncTriggered }: Props) {
  const [syncing, setSyncing] = useState(false);
  const config = SOURCE_CONFIG[integration.source] || {
    label: integration.source,
    icon: "🔌",
    color: "bg-gray-50 border-gray-200",
  };

  const triggerSync = async () => {
    setSyncing(true);
    try {
      await integrationApi.triggerSync(integration.id);
      toast.success(`${config.label} sync started`);
      onSyncTriggered();
    } catch {
      toast.error("Failed to trigger sync");
    } finally {
      setSyncing(false);
    }
  };

  const connectOAuth = async () => {
    try {
      const url = await integrationApi.getOAuthUrl(integration.source);
      window.open(url, "_blank", "width=600,height=700");
    } catch {
      toast.error("Failed to initiate OAuth");
    }
  };

  return (
    <div className={`border rounded-xl p-5 ${config.color}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className="font-semibold text-gray-900">{config.label}</h3>
            <p className="text-xs text-gray-500">{integration.display_name || "Not configured"}</p>
          </div>
        </div>
        <StatusBadge isActive={integration.is_active} />
      </div>

      <div className="mt-4 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {integration.last_synced_at
            ? `Last synced ${format(new Date(integration.last_synced_at), "MMM d, h:mm a")}`
            : "Never synced"}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        {!integration.is_active ? (
          <button
            onClick={connectOAuth}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white text-xs rounded-lg hover:bg-brand-700 transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Connect
          </button>
        ) : (
          <button
            onClick={triggerSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 text-gray-700 text-xs rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Starting..." : "Sync Now"}
          </button>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
        isActive
          ? "bg-green-100 text-green-700"
          : "bg-gray-100 text-gray-500"
      }`}
    >
      {isActive ? (
        <CheckCircle className="w-3 h-3" />
      ) : (
        <XCircle className="w-3 h-3" />
      )}
      {isActive ? "Connected" : "Disconnected"}
    </span>
  );
}
