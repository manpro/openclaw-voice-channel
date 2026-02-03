import { useState, useCallback, useRef } from "react";
import { authFetch } from "../utils/authFetch";

export type ProfileName = "ultra_realtime" | "fast" | "accurate" | "highest_quality";

export interface ProfileConfig {
  label: string;
  description: string;
  chunkIntervalMs: number;
}

export const PROFILES: Record<ProfileName, ProfileConfig> = {
  ultra_realtime: {
    label: "Ultra Realtime",
    description: "Lagsta latens (~1s), Metal GPU, greedy",
    chunkIntervalMs: 1000,
  },
  fast: {
    label: "Snabb",
    description: "Lag latens, Metal GPU, beam=5",
    chunkIntervalMs: 1000,
  },
  accurate: {
    label: "Noggrann",
    description: "Hog kvalitet, medium-modell, CPU",
    chunkIntervalMs: 3000,
  },
  highest_quality: {
    label: "Hogsta Kvalitet",
    description: "Hogsta kvalitet, large-modell, CPU",
    chunkIntervalMs: 3000,
  },
};

export interface WarmupData {
  load_time?: number;
  model?: string;
  backend?: string;
}

interface UseProfileReturn {
  profile: ProfileName;
  setProfile: (p: ProfileName) => void;
  config: ProfileConfig;
  isWarming: boolean;
  warmupData: WarmupData | null;
}

const MIN_WARMUP_DISPLAY_MS = 600;

export function useProfile(): UseProfileReturn {
  const [profile, setProfileState] = useState<ProfileName>("accurate");
  const [isWarming, setIsWarming] = useState(false);
  const [warmupData, setWarmupData] = useState<WarmupData | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const setProfile = useCallback((p: ProfileName) => {
    // Abort any in-flight warmup
    if (abortRef.current) {
      abortRef.current.abort();
    }

    setProfileState(p);
    setIsWarming(true);
    setWarmupData(null);

    const controller = new AbortController();
    abortRef.current = controller;
    const startTime = Date.now();

    authFetch(`/api/warmup?profile=${p}`, {
      method: "POST",
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!controller.signal.aborted) {
          const elapsed = Date.now() - startTime;
          const remaining = Math.max(0, MIN_WARMUP_DISPLAY_MS - elapsed);
          setWarmupData({
            load_time: data.load_time,
            model: data.model,
            backend: data.backend,
          });
          setTimeout(() => {
            if (!controller.signal.aborted) {
              setIsWarming(false);
            }
          }, remaining);
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Warmup failed:", err);
          if (!controller.signal.aborted) {
            const elapsed = Date.now() - startTime;
            const remaining = Math.max(0, MIN_WARMUP_DISPLAY_MS - elapsed);
            setTimeout(() => {
              if (!controller.signal.aborted) {
                setIsWarming(false);
              }
            }, remaining);
          }
        }
      });
  }, []);

  return {
    profile,
    setProfile,
    config: PROFILES[profile],
    isWarming,
    warmupData,
  };
}
