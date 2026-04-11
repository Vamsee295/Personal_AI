/**
 * lib/agentApi.ts – Agent-specific API utilities for the System Control page.
 * Wraps all Step 1-3 backend endpoints with consistent error handling.
 */

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ApiResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface ExecuteResult {
  command: string;
  parsed_action: Record<string, unknown>;
  result: { success: boolean; action: string; message?: string; error?: string };
  raw_llm_response: string;
}

export interface VisionLoopStep {
  step: number;
  screen_text: string;
  action: Record<string, unknown>;
  result: Record<string, unknown>;
  stopped_early?: boolean;
}

export interface HealthStatus {
  status: string;
  ollama_running: boolean;
  model: string;
  version: string;
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      return {
        success: false,
        error: typeof err.detail === "string"
          ? err.detail
          : JSON.stringify(err.detail) || `HTTP ${res.status}`,
      };
    }

    const data = await res.json() as T;
    return { success: true, data };
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Network error";
    return { success: false, error: msg };
  }
}

// ── Step 1 — Execute action ───────────────────────────────────────────────────

/** Send a natural-language command → Ollama → action_executor */
export async function executeCommand(
  command: string,
  model?: string
): Promise<ApiResult<ExecuteResult>> {
  return apiFetch<ExecuteResult>("/api/execute", {
    method: "POST",
    body: JSON.stringify({ command, model }),
  });
}

/** Execute a raw action dict directly, bypassing the LLM */
export async function executeDirectAction(
  action: Record<string, unknown>
): Promise<ApiResult<{ result: Record<string, unknown> }>> {
  return apiFetch("/api/execute/direct", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

// ── Step 2 — Vision endpoints ─────────────────────────────────────────────────

/** Capture screen + OCR + LLM → returns suggested action JSON (no execution) */
export async function analyzeScreen(
  goal: string,
  model?: string
): Promise<ApiResult> {
  return apiFetch("/api/vision/analyze-screen", {
    method: "POST",
    body: JSON.stringify({ goal, model }),
  });
}

/** Run the full autonomous vision → decide → act loop */
export async function runVisionLoop(
  goal: string,
  maxSteps = 5,
  model?: string
): Promise<ApiResult<{ total_steps: number; step_log: VisionLoopStep[] }>> {
  return apiFetch("/api/vision/vision-loop", {
    method: "POST",
    body: JSON.stringify({ goal, max_steps: maxSteps, model }),
  });
}

/** Get current screen as base64 PNG */
export async function getScreenshot(): Promise<ApiResult<{ image_base64: string; width: number; height: number }>> {
  return apiFetch("/api/vision/screenshot");
}

/** Get OCR text from screen */
export async function getScreenOcr(): Promise<ApiResult<{ text: string; char_count: number }>> {
  return apiFetch("/api/vision/ocr");
}

// ── Step 3 — WhatsApp ─────────────────────────────────────────────────────────

/** Send a WhatsApp message via Selenium */
export async function sendWhatsApp(
  contact: string,
  message: string
): Promise<ApiResult<{ contact: string; chat_opened: string }>> {
  return apiFetch("/whatsapp/send", {
    method: "POST",
    body: JSON.stringify({ contact, message }),
  });
}

/** Read recent messages from a WhatsApp chat */
export async function readWhatsApp(
  contact: string,
  count = 5
): Promise<ApiResult<{ messages: Array<{ sender: string; text: string; time: string }> }>> {
  return apiFetch("/whatsapp/read", {
    method: "POST",
    body: JSON.stringify({ contact, count }),
  });
}

// ── Health & status ───────────────────────────────────────────────────────────

/** Check backend health + Ollama status */
export async function getHealth(): Promise<ApiResult<HealthStatus>> {
  return apiFetch<HealthStatus>("/api/health");
}

/** Check if Ollama is reachable */
export async function checkOllama(): Promise<boolean> {
  try {
    const res = await fetch("http://localhost:11434/", { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Screenshot (latest saved file) ────────────────────────────────────────────

/** Returns a URL string pointing to the latest screenshot endpoint */
export function getLatestScreenshotUrl(): string {
  return `${BASE_URL}/api/screenshot/latest?ts=${Date.now()}`;
}

// ── Memory ────────────────────────────────────────────────────────────────────

export interface MemoryCommand {
  id: number;
  timestamp: string;
  user_input: string;
  action_taken: Record<string, unknown>;
  result: string;
  success: boolean;
  duration_ms: number;
  relative_time: string;
}

export interface MemoryStats {
  total_commands: number;
  success_rate: number;
  most_used_action: string;
  preferences_count: number;
  db_size_kb: number;
}

/** Fetch recent commands from memory (paginated) */
export async function getMemoryRecent(
  limit = 20,
  offset = 0
): Promise<ApiResult<{ commands: MemoryCommand[]; total_commands: number }>> {
  return apiFetch(`/memory/recent?limit=${limit}&offset=${offset}`);
}

/** Fetch memory statistics */
export async function getMemoryStats(): Promise<ApiResult<MemoryStats>> {
  return apiFetch<MemoryStats>("/memory/stats");
}

/** Fetch all preferences */
export async function getPreferences(): Promise<ApiResult<{ preferences: Record<string, string> }>> {
  return apiFetch("/memory/preferences");
}

/** Manually save a preference */
export async function savePreference(
  key: string,
  value: string
): Promise<ApiResult<{ key: string; value: string }>> {
  return apiFetch("/memory/preference", {
    method: "POST",
    body: JSON.stringify({ key, value }),
  });
}

/** Delete commands older than N days */
export async function clearOldMemories(days = 30): Promise<ApiResult<{ deleted: number }>> {
  return apiFetch(`/memory/clear?days=${days}`, { method: "DELETE" });
}

