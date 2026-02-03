#!/usr/bin/env python3
"""whisper-cli — Command-line client for whisper-svenska.

Thin wrapper around /api/ingest and /api/interpret endpoints.

Usage:
    whisper-cli file recording.wav --context meeting --profile accurate
    whisper-cli interpret SESSION_ID --context journal
    whisper-cli sessions
    whisper-cli contexts

Requires:
    pip install httpx

Environment:
    WHISPER_URL     Base URL (default: https://localhost:32222)
    WHISPER_TOKEN   Bearer token for auth (optional)
"""
import argparse
import json
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("Krav: pip install httpx", file=sys.stderr)
    sys.exit(1)

BASE_URL = os.environ.get("WHISPER_URL", "https://localhost:32222")
TOKEN = os.environ.get("WHISPER_TOKEN", "")


def _headers() -> dict:
    h = {}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers=_headers(),
        verify=False,
        timeout=300.0,
    )


def cmd_file(args):
    """Ingest an audio file."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"Filen finns inte: {filepath}", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(filepath)
    params = {"profile": args.profile, "source": "cli"}
    if args.context:
        params["context"] = args.context

    with _client() as client:
        with open(filepath, "rb") as f:
            print(f"Laddar upp {filename}...")
            resp = client.post(
                "/api/ingest",
                files={"file": (filename, f)},
                params=params,
            )

        if resp.status_code != 200:
            print(f"Fel: {resp.status_code} — {resp.text}", file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        session_id = data["session_id"]
        job_id = data.get("job_id")
        print(f"Session: {session_id}")
        print(f"Text: {data.get('text', '')[:200]}")

        if job_id and not args.no_wait:
            print(f"\nVantar pa bearbetning (jobb {job_id})...")
            _poll_job(client, job_id)
            _print_session(client, session_id, args.context)


def cmd_interpret(args):
    """Reinterpret an existing session."""
    with _client() as client:
        resp = client.post(
            f"/api/interpret/{args.session_id}",
            params={"context": args.context},
        )

        if resp.status_code != 200:
            print(f"Fel: {resp.status_code} — {resp.text}", file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        job_id = data["job_id"]
        print(f"Tolkningsjobb startat: {job_id}")

        if not args.no_wait:
            print(f"Vantar pa bearbetning...")
            _poll_job(client, job_id)
            _print_session(client, args.session_id, args.context)


def cmd_sessions(args):
    """List sessions."""
    with _client() as client:
        resp = client.get("/api/sessions", params={"limit": args.limit})
        if resp.status_code != 200:
            print(f"Fel: {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        sessions = resp.json().get("sessions", [])
        if not sessions:
            print("Inga sessioner hittades.")
            return

        for s in sessions:
            dur = s.get("duration", 0)
            dur_str = f"{int(dur // 60)}m{int(dur % 60)}s" if dur else "?"
            status = s.get("processing_status", "")
            text = (s.get("text") or "")[:80]
            print(f"  {s['session_id']}  [{s.get('profile', '?')}]  {dur_str}  {status}")
            if text:
                print(f"    {text}")


def cmd_contexts(args):
    """List available context profiles."""
    with _client() as client:
        resp = client.get("/api/contexts")
        if resp.status_code != 200:
            print(f"Fel: {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        contexts = resp.json().get("contexts", [])
        for c in contexts:
            print(f"  {c['name']:15s} {c['label']} — {c['description']}")


def _poll_job(client: httpx.Client, job_id: str):
    """Poll job until completion."""
    while True:
        resp = client.get(f"/api/jobs/{job_id}")
        if resp.status_code != 200:
            print(f"Kunde inte hamta jobbstatus: {resp.status_code}", file=sys.stderr)
            return

        job = resp.json()
        status = job["status"]
        step = job.get("current_step", "")

        sys.stdout.write(f"\r  [{status}] {step}        ")
        sys.stdout.flush()

        if status in ("completed", "failed"):
            print()
            if status == "failed":
                print(f"Jobb misslyckades: {job.get('error', '?')}", file=sys.stderr)
            return

        time.sleep(1)


def _print_session(client: httpx.Client, session_id: str, context: str | None = None):
    """Print session result."""
    resp = client.get(f"/api/sessions/{session_id}")
    if resp.status_code != 200:
        return

    session = resp.json()

    # Pick the right interpretation to display
    data = None
    if context and "interpretations" in session:
        data = session["interpretations"].get(context)
    if not data:
        data = session.get("processed")

    if data and data.get("summary"):
        summary = data["summary"]
        print(f"\nSammanfattning:")
        print(f"  {summary.get('summary', '')}")
        items = summary.get("action_items", [])
        if items:
            print(f"\nAction items:")
            for item in items:
                print(f"  - {item}")

    segments = (data or {}).get("segments", session.get("segments", []))
    print(f"\nSegment ({len(segments)}):")
    for seg in segments[:20]:
        text = seg.get("processed_text") or seg.get("text", "")
        speaker = seg.get("speaker_id", "")
        start = seg.get("start", 0)
        prefix = f"[{speaker}] " if speaker else ""
        m, s = divmod(int(start), 60)
        print(f"  {m}:{s:02d} {prefix}{text}")

    if len(segments) > 20:
        print(f"  ... och {len(segments) - 20} till")


def main():
    parser = argparse.ArgumentParser(
        prog="whisper-cli",
        description="CLI for whisper-svenska",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # file
    p_file = sub.add_parser("file", help="Transkribera en audiofil")
    p_file.add_argument("file", help="Sokvag till audiofil")
    p_file.add_argument("--context", "-c", default=None, help="Context-profil")
    p_file.add_argument("--profile", "-p", default="accurate", help="Transkriberingsprofil")
    p_file.add_argument("--no-wait", action="store_true", help="Vanta inte pa bearbetning")
    p_file.set_defaults(func=cmd_file)

    # interpret
    p_interp = sub.add_parser("interpret", help="Omtolka en befintlig session")
    p_interp.add_argument("session_id", help="Session-ID")
    p_interp.add_argument("--context", "-c", required=True, help="Context-profil")
    p_interp.add_argument("--no-wait", action="store_true", help="Vanta inte pa bearbetning")
    p_interp.set_defaults(func=cmd_interpret)

    # sessions
    p_sess = sub.add_parser("sessions", help="Lista sessioner")
    p_sess.add_argument("--limit", "-n", type=int, default=20, help="Max antal")
    p_sess.set_defaults(func=cmd_sessions)

    # contexts
    p_ctx = sub.add_parser("contexts", help="Lista context-profiler")
    p_ctx.set_defaults(func=cmd_contexts)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
