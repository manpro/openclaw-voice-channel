import { useSessions, SessionSummary } from "../hooks/useSessions";

function StatusBadge({ status }: { status?: string }) {
  if (!status) return null;

  const styles: Record<string, string> = {
    submitted: "bg-blue-900/50 text-blue-300 border-blue-700",
    processing: "bg-blue-900/50 text-blue-300 border-blue-700",
    completed: "bg-green-900/50 text-green-300 border-green-700",
    failed: "bg-red-900/50 text-red-300 border-red-700",
  };

  const labels: Record<string, string> = {
    submitted: "Bearbetar…",
    processing: "Bearbetar…",
    completed: "Klar",
    failed: "Misslyckades",
  };

  const cls = styles[status] ?? "bg-gray-800 text-gray-400 border-gray-600";
  const label = labels[status] ?? status;

  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${cls}`}>
      {(status === "submitted" || status === "processing") && (
        <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
      )}
      {label}
    </span>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("sv-SE", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

interface Props {
  onSelect: (sessionId: string) => void;
}

export function SessionList({ onSelect }: Props) {
  const { sessions, loading, refresh } = useSessions();

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300">Sessioner</h2>
        <button
          onClick={refresh}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Uppdatera
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-gray-500">Laddar…</p>
      ) : sessions.length === 0 ? (
        <p className="text-xs text-gray-500">Inga sessioner sparade.</p>
      ) : (
        <ul className="space-y-2 max-h-[400px] overflow-y-auto">
          {sessions.map((s) => (
            <li
              key={s.session_id}
              onClick={() => onSelect(s.session_id)}
              className="flex flex-col gap-1 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-gray-600 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {formatDate(s.started_at)}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {formatDuration(s.duration)}
                  </span>
                  <StatusBadge status={s.processing_status} />
                </div>
              </div>
              <p className="text-sm text-gray-200 truncate">
                {s.text || <span className="text-gray-500 italic">Tomt transkript</span>}
              </p>
              <span className="text-xs text-gray-600">{s.profile}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
