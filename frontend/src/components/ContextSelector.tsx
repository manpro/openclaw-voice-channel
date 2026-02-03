import { useState, useEffect } from "react";
import { authFetch } from "../utils/authFetch";

interface ContextProfile {
  name: string;
  label: string;
  description: string;
}

interface Props {
  selected: string;
  onChange: (context: string) => void;
  disabled?: boolean;
}

export function ContextSelector({ selected, onChange, disabled }: Props) {
  const [contexts, setContexts] = useState<ContextProfile[]>([]);

  useEffect(() => {
    authFetch("/api/contexts")
      .then((r) => r.json())
      .then((data) => setContexts(data.contexts ?? []))
      .catch(() => {});
  }, []);

  if (contexts.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-gray-400 shrink-0">Tolkning:</label>
      <select
        value={selected}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="bg-gray-800 text-gray-200 text-sm rounded border border-gray-700 px-2 py-1 focus:outline-none focus:border-blue-500 disabled:opacity-50"
      >
        {contexts.map((c) => (
          <option key={c.name} value={c.name} title={c.description}>
            {c.label}
          </option>
        ))}
      </select>
    </div>
  );
}
