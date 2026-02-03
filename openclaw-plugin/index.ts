import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { emptyPluginConfigSchema } from "openclaw/plugin-sdk";
import { webVoicePlugin } from "./src/channel.js";
import { setWebVoiceRuntime } from "./src/runtime.js";

const plugin = {
  id: "openclaw-web-voice",
  name: "Web Voice Chat",
  description: "Browser-based voice chat channel with Swedish STT/TTS",
  configSchema: emptyPluginConfigSchema(),

  register(api: OpenClawPluginApi) {
    setWebVoiceRuntime(api.runtime);
    api.registerChannel({ plugin: webVoicePlugin });
  },
};

export default plugin;
