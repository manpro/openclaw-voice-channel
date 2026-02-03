import { useState, useEffect } from "react";
import { useJobPolling } from "../hooks/useJobPolling";
import { useInterpretation } from "../hooks/useInterpretation";
import { ContextSelector } from "./ContextSelector";
import { authFetch } from "../utils/authFetch";

interface Segment {
  text: string;
  start: number;
  end: number;
  speaker_id?: string;
  low_confidence?: boolean;
  has_pii?: boolean;
  pii_flags?: Array<{ type: string; start_char: number; end_char: number; text: string }>;
  processed_text?: string;
  detected_language?: string;
  language_switch?: boolean;
  word_confidence_avg?: number;
}

interface InterpretationData {
  segments: Segment[];
  summary?: { summary: string; action_items?: string[] };
  context_profile?: string;
  language?: string;
}

interface SessionData {
  session_id: string;
  profile: string;
  started_at: string;
  ended_at: string;
  duration: number;
  text: string;
  segments: Segment[];
  job_id?: string;
  processing_status?: string;
  processed?: {
    segments: Segment[];
    summary?: { summary: string; action_items?: string[] };
    language?: string;
  };
  interpretations?: Record<string, InterpretationData>;
}

const SPEAKER_COLORS = [
  "text-sky-300 bg-sky-900/30 border-sky-700/50",
  "text-emerald-300 bg-emerald-900/30 border-emerald-700/50",
  "text-amber-300 bg-amber-900/30 border-amber-700/50",
  "text-purple-300 bg-purple-900/30 border-purple-700/50",
  "text-rose-300 bg-rose-900/30 border-rose-700/50",
  "text-cyan-300 bg-cyan-900/30 border-cyan-700/50",
];

function speakerColor(speakerId: string | undefined, map: Map<string, number>): string {
  if (!speakerId || speakerId === "UNKNOWN") return "text-gray-400 bg-gray-800/50 border-gray-700/50";
  if (!map.has(speakerId)) {
    map.set(speakerId, map.size % SPEAKER_COLORS.length);
  }
  return SPEAKER_COLORS[map.get(speakerId)!];
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const PIPELINE_STEPS = [
  "confidence",
  "retry",
  "diarization",
  "language_detect",
  "text_processing",
  "pii_flagging",
  "summary",
  "done",
];

function PipelineProgress({ currentStep }: { currentStep: string }) {
  const currentIdx = PIPELINE_STEPS.indexOf(currentStep);
  return (
    <div className="flex items-center gap-1 py-2">
      {PIPELINE_STEPS.map((step, i) => {
        const isActive = i === currentIdx;
        const isDone = i < currentIdx || currentStep === "done";
        return (
          <div key={step} className="flex items-center gap-1">
            <div
              className={`h-2 w-8 rounded-full transition-colors ${
                isDone
                  ? "bg-green-500"
                  : isActive
                  ? "bg-blue-500 animate-pulse"
                  : "bg-gray-700"
              }`}
              title={step}
            />
          </div>
        );
      })}
      <span className="text-xs text-gray-500 ml-2">{currentStep}</span>
    </div>
  );
}

function renderTextWithPii(text: string, piiFlags?: Segment["pii_flags"]) {
  if (!piiFlags || piiFlags.length === 0) return <>{text}</>;

  const parts: React.ReactNode[] = [];
  let lastIdx = 0;

  const sorted = [...piiFlags].sort((a, b) => a.start_char - b.start_char);
  for (const flag of sorted) {
    if (flag.start_char > lastIdx) {
      parts.push(text.slice(lastIdx, flag.start_char));
    }
    parts.push(
      <span
        key={`${flag.start_char}-${flag.end_char}`}
        className="bg-yellow-700/40 text-yellow-200 px-0.5 rounded cursor-help"
        title={`PII: ${flag.type} — "${flag.text}"`}
      >
        {text.slice(flag.start_char, flag.end_char)}
      </span>
    );
    lastIdx = flag.end_char;
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx));
  }
  return <>{parts}</>;
}

function SegmentList({ segments }: { segments: Segment[] }) {
  const speakerMap = new Map<string, number>();

  return (
    <div className="space-y-1 max-h-[500px] overflow-y-auto">
      {segments.map((seg, i) => {
        const text = seg.processed_text ?? seg.text;
        const isWeak = seg.low_confidence;
        const hasSpeaker = !!seg.speaker_id;
        const color = speakerColor(seg.speaker_id, speakerMap);

        return (
          <div
            key={i}
            className={`flex gap-2 px-2 py-1.5 rounded text-sm ${
              isWeak ? "bg-orange-900/20 border border-orange-800/30" : ""
            }`}
          >
            <span className="text-xs text-gray-600 font-mono shrink-0 pt-0.5 w-12">
              {formatTime(seg.start)}
            </span>

            {hasSpeaker && (
              <span
                className={`text-xs px-1.5 py-0.5 rounded border shrink-0 ${color}`}
              >
                {seg.speaker_id}
              </span>
            )}

            <span className="text-gray-200 flex-1">
              {seg.has_pii ? renderTextWithPii(text, seg.pii_flags) : text}
            </span>

            {isWeak && (
              <span
                className="text-xs text-orange-400 shrink-0 pt-0.5 cursor-help"
                title={`Konfidens: ${seg.word_confidence_avg?.toFixed(2) ?? "lag"}`}
              >
                &#9888;
              </span>
            )}

            {seg.language_switch && (
              <span
                className="text-xs text-violet-400 shrink-0 pt-0.5 cursor-help"
                title={`Detekterat sprak: ${seg.detected_language}`}
              >
                {seg.detected_language}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SummaryView({ summary }: { summary: { summary: string; action_items?: string[] } }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 space-y-2">
      <h3 className="text-xs font-semibold text-gray-300">Sammanfattning</h3>
      <p className="text-sm text-gray-200">{summary.summary}</p>
      {summary.action_items && summary.action_items.length > 0 && (
        <ul className="text-xs text-gray-400 list-disc list-inside">
          {summary.action_items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

type TabKey = "processed" | string;

interface Props {
  sessionId: string;
  onBack: () => void;
}

export function SessionDetail({ sessionId, onBack }: Props) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("processed");
  const [interpretContext, setInterpretContext] = useState("meeting");
  const jobStatus = useJobPolling(session?.job_id ?? null);
  const interpretation = useInterpretation();

  const loadSession = async () => {
    try {
      const resp = await authFetch(`/api/sessions/${sessionId}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setSession(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    let active = true;
    setLoading(true);

    const load = async () => {
      try {
        const resp = await authFetch(`/api/sessions/${sessionId}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (active) setSession(data);
      } catch {
        // ignore
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [sessionId]);

  // Reload session when job completes
  useEffect(() => {
    if (jobStatus?.status === "completed") {
      loadSession();
    }
  }, [jobStatus?.status, sessionId]);

  // Reload session when interpretation job completes
  useEffect(() => {
    if (interpretation.jobStatus?.status === "completed") {
      loadSession().then(() => {
        // Switch to the newly created interpretation tab
        const ctx = interpretContext;
        setActiveTab(ctx);
        interpretation.reset();
      });
    }
  }, [interpretation.jobStatus?.status]);

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <p className="text-sm text-gray-500">Laddar session...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <p className="text-sm text-red-400">Session hittades inte.</p>
        <button onClick={onBack} className="mt-2 text-sm text-blue-400 hover:underline">
          Tillbaka
        </button>
      </div>
    );
  }

  const processed = session.processed;
  const interpretations = session.interpretations ?? {};
  const isProcessing =
    session.processing_status === "submitted" || session.processing_status === "processing";

  // Build tabs
  const tabs: { key: TabKey; label: string }[] = [];
  if (processed) {
    tabs.push({ key: "processed", label: "Standard" });
  }
  for (const name of Object.keys(interpretations)) {
    tabs.push({ key: name, label: name.charAt(0).toUpperCase() + name.slice(1) });
  }
  tabs.push({ key: "raw", label: "Ratt" });

  // Determine which data to display
  let displaySegments: Segment[] = session.segments ?? [];
  let displaySummary: { summary: string; action_items?: string[] } | undefined;
  let tabLabel = "Rattranskript";

  if (activeTab === "processed" && processed) {
    displaySegments = processed.segments ?? session.segments ?? [];
    displaySummary = processed.summary;
    tabLabel = "Bearbetade segment";
  } else if (activeTab === "raw") {
    displaySegments = session.segments ?? [];
    displaySummary = undefined;
    tabLabel = "Rattranskript";
  } else if (interpretations[activeTab]) {
    const interp = interpretations[activeTab];
    displaySegments = interp.segments ?? session.segments ?? [];
    displaySummary = interp.summary;
    tabLabel = `Tolkning: ${activeTab}`;
  }

  const handleInterpret = () => {
    interpretation.interpret(sessionId, interpretContext);
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          &larr; Tillbaka
        </button>
        <span className="text-xs text-gray-500">{session.session_id}</span>
      </div>

      {/* Metadata */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-400">
        <span>Profil: {session.profile}</span>
        <span>
          Langd: {Math.floor(session.duration / 60)}m {Math.round(session.duration % 60)}s
        </span>
        <span>
          Start:{" "}
          {new Date(session.started_at).toLocaleString("sv-SE")}
        </span>
      </div>

      {/* Audio player */}
      <audio
        controls
        src={`/api/sessions/${session.session_id}/audio`}
        className="w-full h-10 rounded"
      />

      {/* Pipeline progress */}
      {isProcessing && jobStatus && (
        <div>
          <p className="text-xs text-blue-300 mb-1">Pipeline kors...</p>
          <PipelineProgress currentStep={jobStatus.current_step} />
        </div>
      )}

      {session.processing_status === "failed" && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 text-xs px-3 py-2 rounded-lg">
          Bearbetning misslyckades
        </div>
      )}

      {/* Interpretation controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <ContextSelector
          selected={interpretContext}
          onChange={setInterpretContext}
          disabled={interpretation.isSubmitting || !!interpretation.jobId}
        />
        <button
          onClick={handleInterpret}
          disabled={interpretation.isSubmitting || (!!interpretation.jobId && interpretation.jobStatus?.status !== "completed" && interpretation.jobStatus?.status !== "failed")}
          className="text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-3 py-1 rounded transition-colors"
        >
          {interpretation.isSubmitting ? "Skickar..." : "Omtolka"}
        </button>
        {interpretation.jobId && interpretation.jobStatus && interpretation.jobStatus.status !== "completed" && interpretation.jobStatus.status !== "failed" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-blue-300">Tolkar...</span>
            <PipelineProgress currentStep={interpretation.jobStatus.current_step} />
          </div>
        )}
        {interpretation.error && (
          <span className="text-xs text-red-400">{interpretation.error}</span>
        )}
      </div>

      {/* Tabs */}
      {tabs.length > 1 && (
        <div className="flex gap-1 border-b border-gray-800 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-xs rounded-t transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-gray-800 text-gray-100 border-b-2 border-blue-500"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Summary */}
      {displaySummary && <SummaryView summary={displaySummary} />}

      {/* Segments */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 mb-2">
          {tabLabel}
          <span className="ml-2 text-gray-600">({displaySegments.length} segment)</span>
        </h3>
        <SegmentList segments={displaySegments} />
      </div>
    </div>
  );
}
