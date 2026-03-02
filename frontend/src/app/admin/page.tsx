"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import type { Integration, SyncLog } from "@/types";
import { integrationApi } from "@/lib/api";
import { isAuthenticated, getStoredUser } from "@/lib/auth";
import { ConnectorCard } from "@/components/admin/ConnectorCard";
import { format } from "date-fns";

export default function AdminPage() {
  const router = useRouter();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = getStoredUser();
    if (!isAuthenticated() || !user?.is_admin) {
      router.replace("/chat");
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [ints, logs] = await Promise.all([
        integrationApi.list(),
        integrationApi.listSyncLogs(),
      ]);
      setIntegrations(ints);
      setSyncLogs(logs);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center gap-3 mb-8">
          <button
            onClick={() => router.push("/chat")}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-sm text-gray-500">Manage data source connections and sync status</p>
          </div>
        </div>

        {/* Connectors */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Data Sources</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {integrations.length === 0 ? (
              <p className="text-sm text-gray-400 col-span-4">No integrations configured.</p>
            ) : (
              integrations.map((integration) => (
                <ConnectorCard
                  key={integration.id}
                  integration={integration}
                  onSyncTriggered={loadData}
                />
              ))
            )}
          </div>
        </section>

        {/* Sync Logs */}
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Recent Sync Jobs</h2>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Source</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Docs</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Triggered</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Started</th>
                </tr>
              </thead>
              <tbody>
                {syncLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      No sync jobs yet
                    </td>
                  </tr>
                ) : (
                  syncLogs.slice(0, 20).map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 last:border-0">
                      <td className="px-4 py-3 font-medium capitalize">{log.integration_source}</td>
                      <td className="px-4 py-3">
                        <StatusPill status={log.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-600">{log.docs_processed}</td>
                      <td className="px-4 py-3 text-gray-500 capitalize">{log.triggered_by}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {format(new Date(log.started_at), "MMM d, h:mm a")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: SyncLog["status"] }) {
  const styles = {
    running: "bg-blue-100 text-blue-700",
    success: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    partial: "bg-yellow-100 text-yellow-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
