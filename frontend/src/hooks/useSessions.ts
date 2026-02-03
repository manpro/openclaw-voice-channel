import { useState, useEffect, useCallback } from "react";
import { authFetch } from "../utils/authFetch";

export interface SessionSummary {
  session_id: string;
  profile: string;
  started_at: string;
  duration: number;
  text: string;
  chunks: number;
  job_id?: string;
  processing_status?: string;
}

export function useSessions() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const resp = await authFetch("/api/sessions?limit=50");
      if (!resp.ok) return;
      const data = await resp.json();
      setSessions(data.sessions ?? []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Auto-refresh every 10s if any session is being processed
  useEffect(() => {
    const hasProcessing = sessions.some(
      (s) => s.processing_status === "submitted" || s.processing_status === "processing"
    );
    if (!hasProcessing) return;

    const interval = setInterval(refresh, 10_000);
    return () => clearInterval(interval);
  }, [sessions, refresh]);

  return { sessions, loading, refresh };
}
