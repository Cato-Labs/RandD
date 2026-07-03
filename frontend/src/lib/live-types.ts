/** Shared types for the live Gemini Live session (browser <-> FastAPI bridge). */

export type LiveRole = "user" | "assistant";

export type LiveToolState =
  | "input-streaming"
  | "input-available"
  | "output-available"
  | "output-error";

export type LiveToolPart = {
  type: `tool-${string}`;
  toolCallId: string;
  toolName: string;
  state: LiveToolState;
  input: unknown;
  output?: unknown;
  errorText?: string;
};

export type LiveTextPart = {
  type: "text";
  text: string;
  state: "streaming" | "done";
};

export type LiveFilePart = {
  type: "file";
  url: string;
  mediaType: string;
  filename?: string;
};

export type LivePart = LiveTextPart | LiveToolPart | LiveFilePart;

export type LiveSegment = {
  id: string;
  text: string;
  startSecond: number;
  endSecond: number;
  role: LiveRole;
};

export type LiveMessage = {
  id: string;
  role: LiveRole;
  parts: LivePart[];
  /** WAV replay of the assistant's spoken audio for this turn (voice mode). */
  audioUrl?: string;
  createdAt: number;
};

export type QueueEntry = {
  id: string;
  text: string;
  files: { url: string; mediaType: string; filename?: string }[];
  status: "pending" | "completed";
};

export type LiveUsage = {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
};

export type AgentCard = {
  name: string;
  model: string;
  instructions: string;
  tools: { name: string; description: string }[];
};

export type LiveVoice = {
  id: string;
  name: string;
  gender: "male" | "female" | "neutral";
  accent: string;
  age: string;
  description: string;
};

export type PersonaState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "asleep";

export type ConnectionStatus = "disconnected" | "connecting" | "connected";

export type SessionMode = "text" | "audio";
