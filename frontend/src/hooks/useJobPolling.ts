import { useState, useEffect } from "react";
import { authFetch } from "../utils/authFetch";

export interface JobStatus {
  id: string;
  status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  error: string;
}

export function useJobPolling(jobId: string | null): JobStatus | null {
  const [job, setJob] = useState<JobStatus | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    let active = true;

    const poll = async () => {
      try {
        const resp = await authFetch(`/api/jobs/${jobId}`);
        if (!resp.ok) return;
        const data: JobStatus = await resp.json();
        if (active) setJob(data);

        // Stop polling when terminal
        if (data.status === "completed" || data.status === "failed") {
          return;
        }
      } catch {
        // ignore
      }

      if (active) {
        setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      active = false;
    };
  }, [jobId]);

  return job;
}
