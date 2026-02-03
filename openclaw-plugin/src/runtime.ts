import type { OpenClawRuntime } from "openclaw/plugin-sdk";

let runtime: OpenClawRuntime | null = null;

export function setWebVoiceRuntime(rt: OpenClawRuntime): void {
  runtime = rt;
}

export function getWebVoiceRuntime(): OpenClawRuntime {
  if (!runtime) {
    throw new Error("Web voice runtime not initialized");
  }
  return runtime;
}
