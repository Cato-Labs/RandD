# DESIGN.md — AI Elements Chat + Voice UI

North-star document for the RandD AI chat surface. The frontend is built **exclusively** from
[Vercel AI Elements](https://github.com/vercel/ai-elements) components (shadcn/ui-based), wired to
**live data** from a Strands `BidiAgent` running **Gemini Live** — never simulated/demo data.

---

## 1. Sourcing & sync strategy ("fork + sync")

AI Elements is distributed shadcn-style: component **source is copied into the consuming app** and
owned by it. We mirror upstream `vercel/ai-elements` and keep it fresh:

- Vendored source lives in `frontend/src/components/ai-elements/` (elements) and
  `frontend/src/components/ui/` (the upstream `@repo/shadcn-ui` primitives, kept byte-compatible so
  upstream diffs apply cleanly).
- `scripts/sync-ai-elements.sh` re-downloads the upstream default branch (or a fork via
  `AI_ELEMENTS_REPO=<owner>/<repo>`), re-vendors every component we consume, and rewrites the
  monorepo import aliases:
  - `@repo/shadcn-ui/components/ui/*` → `@/components/ui/*`
  - `@repo/shadcn-ui/lib/utils` → `@/lib/utils`
  - `@repo/shadcn-ui/hooks/*` → `@/hooks/*`
- To formally fork: create `ImRonAI/ai-elements` on GitHub from `vercel/ai-elements` and enable
  GitHub's "Sync fork" (or a scheduled workflow). Point the sync script at the fork with
  `AI_ELEMENTS_REPO=ImRonAI/ai-elements`. (Forks cannot be created from this sandbox; the sync
  script consumes upstream directly until the fork exists.)
- **No wrapper components.** AI Elements sub-components are composed **directly in JSX** in app
  views. We never re-export a library behind a generic prop API.

## 2. Design system

Tokens are CSS variables (shadcn "CSS Variables mode", required by AI Elements) declared in
`frontend/src/index.css` with Tailwind v4 `@theme inline` mapping. All AI Elements components
consume these tokens, so restyling is centralized here.

| Token | Light | Dark | Usage |
|---|---|---|---|
| `--background` / `--foreground` | `oklch(0.985 0.002 95)` / `oklch(0.216 0.006 56)` | `oklch(0.216 0.006 56)` / `oklch(0.985 0.002 95)` | App canvas & text |
| `--primary` | `oklch(0.558 0.165 254)` (electric blue) | same | Submit, active states, persona tint |
| `--accent` | `oklch(0.938 0.012 255)` | `oklch(0.31 0.02 255)` | Hovers, chips |
| `--muted` / `--muted-foreground` | subtle warm grays | | Transcripts, secondary labels |
| `--destructive` | `oklch(0.577 0.245 27)` | | Error tool states, mic stop |
| `--border` / `--input` / `--ring` | warm gray ramp | | All component chrome |
| `--radius` | `0.625rem` | | Radius everywhere (AI Elements uses `rounded-lg`/`rounded-xl` derived from it) |

Typography: system UI stack (`font-sans`), `Geist Mono`-fallback mono stack for code
(`CodeBlock`, `Sandbox`, shell output). Layout: a single full-height app shell —
header (agent identity + voice controls) / scrollable `Conversation` / sticky `PromptInput` footer.
Voice mode adds a right-side dock: `Persona`, `Transcription`, `AudioPlayer`.

Dark mode is class-based (`.dark`) and is the default (matches Gemini Live console aesthetics).

## 3. Runtime architecture (live data)

```
Browser (Vite + React 19)                     Python backend (FastAPI)
┌─────────────────────────────┐   WebSocket   ┌─────────────────────────────────┐
│ useLiveAgent() hook          │◄────────────►│ /ws  ⇄  strands BidiAgent        │
│  - mic PCM16 @16k (worklet)  │  JSON events │       BidiGeminiLiveModel        │
│  - plays PCM16 @24k          │              │ tools: editor, shell, load_tool │
│  - message/part store        │   HTTP       │ system: meta-tooling prompt      │
│ AI Elements components       │◄────────────►│ /api/agent /api/tools /workspace │
└─────────────────────────────┘              └─────────────────────────────────┘
```

- The browser streams `bidi_audio_input` / `bidi_text_input` / `bidi_image_input` events verbatim
  into `BidiAgent.send(dict)` (the agent reconstructs TypedEvents from dicts).
- The backend relays every `BidiOutputEvent` (`bidi_transcript_stream`, `bidi_audio_stream`,
  `bidi_interruption`, `bidi_response_start/complete`, `bidi_usage`) plus Strands tool events
  (`tool_use_stream`, `tool_result`) as JSON to the client.
- `useLiveAgent` folds that event stream into a `UIMessage[]`-shaped store (AI SDK part types:
  `text`, `tool-*`, `file`) so AI Elements components consume it natively.
- The **agent has exactly three tools**: `editor`, `shell`, `load_tool`. `load_tool` gives the
  agent runtime tool discovery/creation (meta-tooling) without bloating its context window. The
  system prompt embeds the Strands meta-tooling example's `TOOL_BUILDER_SYSTEM_PROMPT`.
- Tool-created artifacts land in `backend/workspace/`, statically served at `/workspace/*` so the
  UI can preview them (`WebPreview`, `Image`, `Artifact`).

## 4. Chat components — feature-by-feature plan

Every listed feature is wired to real agent/session data. **Reasoning is intentionally excluded**;
`ChainOfThought` is the reasoning surface.

### `Conversation` (+ `ConversationContent`, `ConversationEmptyState`, `ConversationScrollButton`, `ConversationDownload`)
Thread container with `use-stick-to-bottom` auto-scroll. `ConversationEmptyState` renders the
pre-session hero (agent name, suggestions to connect). `ConversationScrollButton` floats when
scrolled up. `ConversationDownload` exports the live thread via `messagesToMarkdown` — free
transcript export for voice sessions too.

### `Message` (+ `MessageContent`, `MessageActions`/`MessageAction`, `MessageToolbar`, `MessageBranch*`)
One per user/assistant turn, `from` driven by event role. `MessageActions` provides copy
(clipboard) and retry (re-`send` of the user turn). `MessageBranch`/`MessageBranchSelector`/
`MessageBranchPrevious|Next|Page` display regenerated alternatives when a turn is retried —
branches are real re-generations stored per turn.

### `Response` → `MessageResponse` (Streamdown)
Token-by-token markdown rendering of streaming transcript deltas (`bidi_transcript_stream`,
role=assistant), with `@streamdown/code` (Shiki), `@streamdown/math` (KaTeX), `@streamdown/mermaid`
and CJK plugins enabled. `parseIncompleteMarkdown` handles mid-stream markdown. This is the
stream-down integration point: deltas append to the active text part until `is_final`.

### `ChainOfThought` (+ `Header`, `Step`, `Content`, `SearchResults`/`SearchResult`, `Image`)
The visible reasoning trail for a turn — **not** the Reasoning component. Each agent action becomes
a `ChainOfThoughtStep` (icon + label + status `complete|active|pending`): model starts responding →
step; tool invoked → step with the tool name; tool result → step completes. `ChainOfThoughtSearchResults`
badges enumerate files touched by `editor`; `ChainOfThoughtImage` embeds image outputs. Collapsible
via `ChainOfThoughtHeader`, auto-opens while streaming (controlled `open` from live state).

### `Task` (+ `TaskTrigger`, `TaskContent`, `TaskItem`, `TaskItemFile`)
Collapsible grouping of related work inside a turn: one `Task` per tool burst (e.g. "Editing
files"), `TaskItem`s appended live from tool input/output deltas, `TaskItemFile` for each file the
`editor`/`shell` tool touches (parsed from real tool args).

### `Tool` (+ `ToolHeader`, `ToolContent`, `ToolInput`, `ToolOutput`)
Canonical renderer for every `tool-*` part. `ToolHeader` shows tool name + live state badge
(`input-streaming` → `input-available` → `output-available`/`output-error`) exactly tracking
Strands `ToolUseStreamEvent`→`ToolResultEvent`. `ToolInput` pretty-prints streamed JSON args in a
`CodeBlock`; `ToolOutput` renders result text/errors. Used for `editor`, `shell`, `load_tool` and
any tool the agent creates at runtime.

### `Sandbox` (+ `SandboxHeader`, `SandboxContent`, `SandboxTabs*`)
Code-execution surface bound to the `shell` tool: tabs for **Command**, **Output**, and **Files**
per execution, populated from the real tool input (`command`) and result (stdout/stderr). Multiple
executions stack as tabbed sandboxes inside the turn.

### `Artifact` (+ `ArtifactHeader`, `ArtifactTitle`, `ArtifactDescription`, `ArtifactActions`/`ArtifactAction`, `ArtifactClose`, `ArtifactContent`)
Side panel that opens when the `editor` tool creates/modifies a file: title = filename, description
= tool action, content = `CodeBlock` of the actual file contents (fetched from `/workspace/...`).
Actions: copy, download, open-in-new-tab; `ArtifactClose` dismisses.

### `WebPreview` (+ `WebPreviewNavigation`, `WebPreviewNavigationButton`, `WebPreviewUrl`, `WebPreviewBody`, `WebPreviewConsole`)
Live iframe preview of **created documents** (HTML/Markdown rendered) served from
`/workspace/…`. Navigation bar with back/forward/refresh buttons, editable `WebPreviewUrl`, and
`WebPreviewConsole` streaming iframe console logs. Opens automatically when the agent writes a
previewable document.

### `Image`
Renders AI SDK `file`/image parts: user image attachments echoed into the thread and any
`image/*` file the agent produces in the workspace (`base64`/`mediaType` contract).

### `Attachments` (+ `Attachment`, `AttachmentPreview`, `AttachmentInfo`, `AttachmentRemove`, `AttachmentHoverCard*`, `AttachmentEmpty`)
Attachment strip inside `PromptInput` (via `usePromptInputAttachments`): image thumbnails via
`AttachmentPreview`, hover card zoom (`AttachmentHoverCard*`), name/size via `AttachmentInfo`,
removal via `AttachmentRemove`. On submit, images are base64-encoded and sent as
`bidi_image_input` to Gemini Live.

### `Agent` (+ `AgentHeader`, `AgentContent`, `AgentInstructions`, `AgentTools`/`AgentTool`, `AgentOutput`)
Renders the **real** agent card fetched from `/api/agent`: model id, the meta-tooling system prompt
in `AgentInstructions`, and `AgentTool` chips for `editor`, `shell`, `load_tool` — plus any tool
the agent `load_tool`s at runtime (registry re-fetched after each `load_tool` result).

### Workflow (`Canvas`, `Node`(+`NodeHeader/Title/Description/Action/Content/Footer`), `Edge`, `Connection`, `Controls`, `Panel`, `Toolbar`)
An xyflow graph of the **live session**: a node for the user, the Gemini Live agent, and each tool;
an animated `Edge` (temporary style while running, permanent when complete) drawn per tool
invocation. `Panel` hosts session stats (token usage from `bidi_usage`), `Toolbar` hosts
fit/zoom actions, `Controls` standard xyflow controls, `Connection` styles the drag preview.
Toggleable "Workflow" view of the same live data.

### `Plan` (+ `PlanHeader`, `PlanTitle`, `PlanDescription`, `PlanAction`, `PlanContent`, `PlanFooter`, `PlanTrigger`)
Streaming plan panel. The system prompt instructs the agent to emit a fenced ` ```plan ` JSON block
when asked to plan multi-step work; the block is parsed live into `Plan` with `Shimmer` streaming
affordance on the in-progress step, `PlanTrigger` collapse, and a `PlanAction` linking to the
workflow view.

### `Queue` (+ `QueueList`, `QueueSection*`, `QueueItem*`)
Real prompt queue: messages submitted while the agent is speaking/streaming are queued client-side
and drained on `bidi_response_complete`. `QueueSection "Queued"` lists pending prompts
(`QueueItemContent`, attachments via `QueueItemAttachment`/`QueueItemImage`/`QueueItemFile`,
cancel via `QueueItemAction`), `QueueSection "Completed"` shows drained ones struck through.

### `PromptInput` (full surface)
`PromptInputProvider` + `PromptInput` form with: `PromptInputBody`, auto-growing
`PromptInputTextarea` (Enter submits, Shift+Enter newline), `PromptInputHeader`/`PromptInputFooter`,
`PromptInputTools`, `PromptInputActionMenu` (+`Trigger/Content/Item`) hosting
`PromptInputActionAddAttachments`, drag-drop + paste attachments (`accept="image/*"`, multiple),
`PromptInputButton` for mic toggle (voice mode) and workflow toggle, `PromptInputSelect`
(+sub-components) for Gemini voice choice mirror, hidden-until-typed `PromptInputCommand` palette
(`/` commands: /plan, /workflow, /clear), and `PromptInputSubmit` whose status mirrors the live
stream (`submitted`→`streaming`→ready/error) enabling stop-on-click (sends interrupt/close).

## 5. Voice components — feature-by-feature plan

Voice mode uses the same thread (all chat components above render voice-session tool
use/transcripts identically). Additions:

### `Persona`
WebGL2 Rive avatar; `state` is derived from real session state: `asleep` (disconnected), `idle`
(connected, quiet), `listening` (mic streaming), `thinking` (turn started, no audio yet),
`speaking` (playing `bidi_audio_stream`). Variant `halo`, tinted `--primary` via dynamic color.

### `AudioPlayer` (+ `AudioPlayerElement`, `AudioPlayerControlBar`, `AudioPlayerPlayButton`, `AudioPlayerSeekBackwardButton`, `AudioPlayerSeekForwardButton`, `AudioPlayerTimeDisplay`, `AudioPlayerTimeRange`, `AudioPlayerDurationDisplay`, `AudioPlayerMuteButton`, `AudioPlayerVolumeRange`)
Assistant audio is captured per turn: streamed PCM chunks are also accumulated into a WAV blob;
when the turn completes a full media-chrome `AudioPlayer` (all sub-controls above) is attached to
that assistant message for replay/seek/mute — real recorded model audio, not a sample file.

### `MicSelector` (+ `MicSelectorTrigger/Content/Input/List/Empty/Item/Label/Value`, `useAudioDevices`)
Device picker backed by `useAudioDevices` (real `enumerateDevices` + permission handling). The
chosen `deviceId` is applied to `getUserMedia` for the 16 kHz PCM capture pipeline; switching
devices live restarts capture.

### `SpeechInput`
Push-to-talk / dictation button in the `PromptInput` toolbar. Its `onTranscriptionChange` fills the
textarea (browser SpeechRecognition path) so users can dictate text prompts even in text mode;
in voice mode the button toggles the raw PCM mic stream to Gemini Live.

### `Transcription` (+ `TranscriptionSegment`)
Word-timed transcript strip under the persona. Segments are built from real
`bidi_transcript_stream` events (user + assistant), timestamped on arrival against the audio
clock so `currentTime` from the `AudioPlayer` highlights the active segment on replay.

### `JSXPreview` (+ `JSXPreviewContent`, `JSXPreviewError`, `useJSXPreview`)
When the model emits fenced ` ```jsx ` in a (voice or text) response, the block streams into
`JSXPreview` (`isStreaming` while the turn is open — auto-completes partial tags) rendering live UI
the agent "draws while talking". `JSXPreviewError` surfaces parse errors.

### `VoiceSelector` (+ `Trigger/Content/Dialog/Input/List/Empty/Group/Item/Shortcut/Separator/Gender/Accent/Age/Name/Description/Attributes/Bullet/Preview`, `useVoiceSelector`)
Command-palette picker over the **real Gemini Live prebuilt voices** (Puck, Charon, Kore, Fenrir,
Aoede, Leda, Orus, Zephyr) served by `/api/voices` with attribute metadata rendered via
`VoiceSelectorGender/Accent/Age/Attributes/Bullet`. Selection reconnects the Live session with
`provider_config.audio.voice` set. `VoiceSelectorDialog` provides the searchable full list.

## 6. Backend plan (Gemini Live agent)

- `backend/app/agent.py` — builds `BidiAgent(model=BidiGeminiLiveModel(...), tools=[editor, shell,
  load_tool], system_prompt=META_TOOLING_PROMPT + UI contract)`. Model id
  `gemini-3.1-flash-live-preview` (override with `GEMINI_LIVE_MODEL`), voice/mode from
  the WebSocket query (`?mode=audio|text&voice=Puck`). `GOOGLE_API_KEY` required.
- `backend/app/main.py` — FastAPI: `WS /ws` (one BidiAgent per connection, driven end-to-end by the
  vendored harness loop: `BidiAgent.run(inputs=[BidiWebSocketInput], outputs=[BidiWebSocketOutput])`
  where the IO channels implement the vendored `BidiInput`/`BidiOutput` protocols — the harness owns
  task supervision, concurrent tool execution, interruption and `stop_all` teardown), `GET
  /api/agent`, `GET /api/tools` (live tool registry — reflects `load_tool` additions), `GET
  /api/voices`, static `/workspace`. Tool execution is sandboxed to `backend/workspace/` (cwd) and
  `shell` runs non-interactive (`STRANDS_NON_INTERACTIVE=true`, `BYPASS_TOOL_CONSENT=true`).
- Meta-tooling: system prompt embeds the Strands meta-tooling example's
  `TOOL_BUILDER_SYSTEM_PROMPT` verbatim (tool naming/creation/usage/structure rules), so the agent
  creates tool files with `editor`, hot-loads them with `load_tool`, and keeps its context window
  small by discovering tools on demand.

## 7. Repository layout

```
frontend/                  Vite + React 19 + Tailwind v4 + vendored AI Elements
  src/components/ai-elements/   vendored elements (sync script target)
  src/components/ui/            vendored shadcn/ui primitives
  src/hooks/use-live-agent.ts   ws bridge → UIMessage store (live data only)
  src/lib/audio.ts              PCM16 worklet capture + streaming playback + WAV capture
  src/views/                    App shell composing AI Elements directly (no wrappers)
backend/                   FastAPI + strands-agents (BidiAgent / Gemini Live)
scripts/sync-ai-elements.sh    upstream/fork sync
```

## 8. Run & test

See README "AI Chat (Gemini Live)" section: `backend` → `pip install -r requirements.txt`,
`GOOGLE_API_KEY=… uvicorn app.main:app`; `frontend` → `npm i && npm run dev`; open
http://localhost:5173, pick a voice + mic, connect, speak or type; ask the agent to create a tool
("make a tool that ...") to exercise editor/shell/load_tool meta-tooling and watch `Tool`,
`Sandbox`, `Artifact`, `WebPreview`, workflow canvas update from live events.
