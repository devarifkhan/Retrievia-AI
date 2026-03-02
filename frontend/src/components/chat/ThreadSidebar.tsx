"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Plus, Trash2, LogOut, Settings } from "lucide-react";
import toast from "react-hot-toast";
import type { Thread } from "@/types";
import { chatApi } from "@/lib/api";
import { logout, getStoredUser } from "@/lib/auth";
import { format } from "date-fns";

export function ThreadSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [threads, setThreads] = useState<Thread[]>([]);
  const user = getStoredUser();

  useEffect(() => {
    chatApi.listThreads().then(setThreads).catch(() => {});
  }, [pathname]);

  const createThread = async () => {
    try {
      const thread = await chatApi.createThread();
      setThreads((prev) => [thread, ...prev]);
      router.push(`/chat/${thread.id}`);
    } catch {
      toast.error("Failed to create conversation");
    }
  };

  const deleteThread = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await chatApi.deleteThread(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
      if (pathname === `/chat/${id}`) router.push("/chat");
    } catch {
      toast.error("Failed to delete conversation");
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h1 className="font-bold text-lg tracking-tight">Retrievia</h1>
          {user?.is_admin && (
            <button
              onClick={() => router.push("/admin")}
              className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition"
              title="Admin dashboard"
            >
              <Settings className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={createThread}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition-colors border border-gray-700"
        >
          <Plus className="w-4 h-4" />
          New conversation
        </button>
      </div>

      {/* Thread list */}
      <nav className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
        {threads.length === 0 ? (
          <p className="text-xs text-gray-500 text-center py-6">No conversations yet</p>
        ) : (
          threads.map((thread) => {
            const isActive = pathname === `/chat/${thread.id}`;
            return (
              <button
                key={thread.id}
                onClick={() => router.push(`/chat/${thread.id}`)}
                className={`w-full flex items-start justify-between gap-2 px-3 py-2.5 rounded-lg text-sm text-left group transition-colors ${
                  isActive ? "bg-gray-700 text-white" : "text-gray-300 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium">{thread.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {format(new Date(thread.updated_at), "MMM d")}
                  </p>
                </div>
                <button
                  onClick={(e) => deleteThread(e, thread.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition shrink-0 mt-0.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </button>
            );
          })
        )}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {user?.first_name || user?.username || "User"}
            </p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition shrink-0"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
