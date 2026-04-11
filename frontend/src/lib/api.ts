/**
 * api.ts – Centralised API client for the Ultron backend (localhost:8000)
 */

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatResponse {
  response: string;
  model: string;
  done: boolean;
}

export interface ScreenAnalyseResponse {
  screen_text: string;
  analysis: string;
  image_base64?: string;
}

export interface VoiceListenResponse {
  text: string;
  success: boolean;
}

export interface VoiceRespondResponse {
  command: string;
  ai_response: string;
  spoken: boolean;
  success: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Chat
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Send a chat message and stream the response via a ReadableStream.
 * Uses SSE (text/event-stream). Yields token strings.
 */
export async function* chatStream(
  message: string,
  history: ChatMessage[],
  model = "qwen2.5-coder:7b"
): AsyncGenerator<string> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model, stream: true }),
  });

  if (!res.ok || !res.body) {
    throw new Error("Chat API failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    // SSE format: "data: <token>\n\n"
    for (const line of chunk.split("\n")) {
      if (line.startsWith("data: ")) {
        const token = line.slice(6);
        if (token) yield token;
      }
    }
  }
}

/** Non-streaming fallback */
export async function chat(
  message: string,
  history: ChatMessage[],
  model = "qwen2.5-coder:7b"
): Promise<string> {
  const data = await request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, model, stream: false }),
  });
  return data.response;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Screen AI
// ─────────────────────────────────────────────────────────────────────────────

/** Capture the screen, run OCR, and get an AI analysis */
export async function analyseScreen(): Promise<ScreenAnalyseResponse> {
  return request<ScreenAnalyseResponse>("/api/screen/analyse");
}

/** Just capture the screen as a base64 PNG */
export async function captureScreen(): Promise<{ image_base64: string }> {
  return request("/api/system/screen-capture");
}

// ─────────────────────────────────────────────────────────────────────────────
//  Voice
// ─────────────────────────────────────────────────────────────────────────────

/** Microphone → speech-to-text (backend listens for ~5s) */
export async function voiceListen(): Promise<VoiceListenResponse> {
  return request<VoiceListenResponse>("/api/voice/listen", { method: "POST" });
}

/** Send a text command, get AI response + TTS (backend speaks back) */
export async function voiceRespond(
  command: string,
  model = "qwen2.5-coder:7b",
  speak = false
): Promise<VoiceRespondResponse> {
  return request<VoiceRespondResponse>("/api/voice/respond", {
    method: "POST",
    body: JSON.stringify({ command, model, speak }),
  });
}

/** Full pipeline: listen → AI → speak. Returns transcribed text + AI reply */
export async function voicePipeline(): Promise<VoiceRespondResponse> {
  return request<VoiceRespondResponse>("/api/voice/pipeline", { method: "POST" });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Health
// ─────────────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<{ status: string; ollama_running: boolean }> {
  return request("/api/health");
}
