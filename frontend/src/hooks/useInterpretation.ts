import { useState, useCallback } from "react";
import { authFetch } from "../utils/authFetch";
import { useJobPolling, type JobStatus } from "./useJobPolling";

interface UseInterpretationReturn {
  isSubmitting: boolean;
  jobId: string | null;
  jobStatus: JobStatus | null;
  error: string | null;
  interpret: (sessionId: string, context: string) => Promise<void>;
  reset: () => void;
}

export function useInterpretation(): UseInterpretationReturn {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const jobStatus = useJobPolling(jobId);

  const interpret = useCallback(async (sessionId: string, context: string) => {
    setError(null);
    setIsSubmitting(true);
    setJobId(null);

    try {
      const resp = await authFetch(
        `/api/interpret/${sessionId}?context=${encodeURIComponent(context)}`,
        { method: "POST" },
      );
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setJobId(data.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Okant fel");
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const reset = useCallback(() => {
    setJobId(null);
    setError(null);
    setIsSubmitting(false);
  }, []);

  return { isSubmitting, jobId, jobStatus, error, interpret, reset };
}
