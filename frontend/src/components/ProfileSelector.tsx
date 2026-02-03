import { useState, useEffect, useRef } from "react";
import { PROFILES, type ProfileName, type WarmupData } from "../hooks/useProfile";

interface ProfileSelectorProps {
  profile: ProfileName;
  onSelect: (p: ProfileName) => void;
  disabled?: boolean;
  isWarming?: boolean;
  warmupData?: WarmupData | null;
}

const PROFILE_ORDER: ProfileName[] = [
  "ultra_realtime",
  "fast",
  "accurate",
  "highest_quality",
];

const PROFILE_COLORS: Record<
  ProfileName,
  { active: string; ring: string; dot: string }
> = {
  ultra_realtime: {
    active: "bg-emerald-600 text-white border-emerald-400",
    ring: "ring-emerald-500/40",
    dot: "bg-emerald-400",
  },
  fast: {
    active: "bg-sky-600 text-white border-sky-400",
    ring: "ring-sky-500/40",
    dot: "bg-sky-400",
  },
  accurate: {
    active: "bg-violet-600 text-white border-violet-400",
    ring: "ring-violet-500/40",
    dot: "bg-violet-400",
  },
  highest_quality: {
    active: "bg-amber-600 text-white border-amber-400",
    ring: "ring-amber-500/40",
    dot: "bg-amber-400",
  },
};

const SUCCESS_FLASH_MS = 1500;

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 inline-block ml-1.5 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z"
      />
    </svg>
  );
}

export function ProfileSelector({
  profile,
  onSelect,
  disabled = false,
  isWarming = false,
  warmupData = null,
}: ProfileSelectorProps) {
  const [successFlash, setSuccessFlash] = useState(false);
  const [lastLoadTime, setLastLoadTime] = useState<number | null>(null);
  const prevWarmingRef = useRef(isWarming);

  // Detect transition from warming → done to trigger success flash
  useEffect(() => {
    if (prevWarmingRef.current && !isWarming) {
      if (warmupData?.load_time != null) {
        setLastLoadTime(warmupData.load_time);
      }
      setSuccessFlash(true);
      const timer = setTimeout(() => setSuccessFlash(false), SUCCESS_FLASH_MS);
      return () => clearTimeout(timer);
    }
    prevWarmingRef.current = isWarming;
  }, [isWarming, warmupData]);

  const statusText = () => {
    if (isWarming) {
      const modelName = PROFILES[profile].label;
      return `Laddar ${modelName}...`;
    }
    if (successFlash) {
      const timeStr = lastLoadTime != null ? ` på ${lastLoadTime.toFixed(1)}s` : "";
      return `Klar${timeStr}`;
    }
    return PROFILES[profile].description;
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <h2 className="text-sm font-semibold mb-2 text-gray-400 uppercase tracking-wide">
        Profil
      </h2>
      <div className="flex gap-2">
        {PROFILE_ORDER.map((name) => {
          const cfg = PROFILES[name];
          const colors = PROFILE_COLORS[name];
          const isActive = profile === name;
          const showSpinner = isActive && isWarming;
          return (
            <button
              key={name}
              onClick={() => onSelect(name)}
              disabled={disabled || isWarming}
              title={cfg.description}
              className={`
                flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all
                border-2
                ${
                  isActive
                    ? `${colors.active} ring-2 ${colors.ring}`
                    : "bg-gray-800 text-gray-300 border-transparent hover:bg-gray-700"
                }
                ${isWarming && isActive ? "animate-pulse" : ""}
                ${isWarming && !isActive ? "opacity-30 cursor-not-allowed" : ""}
                ${disabled && !isWarming ? "opacity-50 cursor-not-allowed" : ""}
                ${!disabled && !isWarming ? "cursor-pointer" : ""}
              `}
            >
              {cfg.label}
              {showSpinner && <Spinner />}
            </button>
          );
        })}
      </div>
      <p
        data-testid="profile-status"
        className={`text-xs mt-2 transition-colors duration-300 ${
          successFlash ? "text-green-400 font-medium" : "text-gray-500"
        }`}
      >
        {statusText()}
      </p>
    </div>
  );
}
