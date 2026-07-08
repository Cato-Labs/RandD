# Frontend & Live Voice Console Audit

**Scope:** `frontend/` (Vite + AI Elements demo), `apps/web/` (Next.js target), and the live voice console.  
**Date:** 2026-07-06  
**Read-only audit** — no code files were modified.

---

## Executive Summary

The repository currently contains a **functioning Vite/React live-agent demo** in `frontend/` and an **unscaffolded Next.js starter** in `apps/web/`. The demo proves the realtime BIDI bridge (WebSocket, PCM audio, camera frames, tool rendering, AI Elements) but it is **not the target Next.js PWA**. The production surface described in `AGENTS.md` and `TASKS.md` M7 is almost entirely missing from `apps/web`: no App Router pages, no PWA manifest/service worker, no offline queue, no design-system tokens, no role-aware navigation, no Today/Daily Route, Property Detail, Work Orders, Report viewer, or Ops dashboard. The static `public/inspection.html` is the most complete M7.7 artifact, but it is a standalone file, not integrated into the React app or Next.js.

**Bottom line:** The voice-console technology is de-risked, but the **Next.js PWA product shell is empty** and needs to be built from scratch.

---

## Frontend Architecture

### `frontend/` — Vite demo, not the PWA

- **Stack:** Vite 7 + React 19 + TypeScript + Tailwind CSS v4 (`frontend/package.json:12-46`).
- **Build tool:** `frontend/vite.config.ts`. Proxies `/api`, `/workspace`, `/ws` to `localhost:8000` (`frontend/vite.config.ts:14-18`).
- **State layer:** `use-live-agent.ts` is the single source of truth for a live Gemini Live session (`frontend/src/hooks/use-live-agent.ts:51-834`).
- **AI Elements:** A vendored copy of the AI Elements component library lives under `frontend/src/components/ai-elements/*`. It is used directly by `ChatThread`, `Composer`, `VoiceDock`, etc.
- **UI primitives:** shadcn/ui components are under `frontend/src/components/ui/*` (button, card, dialog, select, tooltip, etc.).
- **Entry point:** `frontend/src/main.tsx` mounts `App.tsx` with StrictMode; no service worker or PWA registration.

### `apps/web/` — Next.js starter, empty product

- **Stack:** Next.js 16.2.10 + React 19 + Tailwind v4 (`apps/web/package.json:11-25`).
- **Config:** `apps/web/next.config.ts` is the default empty object (`apps/web/next.config.ts:3-7`).
- **Pages:** Only the default `apps/web/src/app/page.tsx` (Next.js marketing starter) and `apps/web/src/app/layout.tsx` exist. No routing, no API client, no PWA config.
- **Font:** Uses `Geist` and `Geist_Mono` from `next/font/google` (`apps/web/src/app/layout.tsx:2-13`), but the page body overrides to `Arial, Helvetica, sans-serif` (`apps/web/src/app/globals.css:22-25`).
- **Design system:** `apps/web/src/app/globals.css` only defines two colors (`--background`, `--foreground`) and a dark-mode media query. It does **not** implement `DESIGN.md` tokens.

---

## Live Voice Console Audit

### WebSocket / BIDI bridge

Implemented in `frontend/src/hooks/use-live-agent.ts`:

- Connection URL built with `mode`, `voice`, and `provider` (`use-live-agent.ts:46-49`).
- `connect()` opens a WebSocket, wires `onmessage`, `onclose`, `onerror` (`use-live-agent.ts:548-571`).
- `handleEvent` dispatches backend events: `bidi_connection_start`, `bidi_response_start`, `bidi_transcript_stream`, `bidi_audio_stream`, `bidi_interruption`, `tool_use_stream`, `tool_result`, `bidi_response_complete`, `bidi_usage`, `bidi_error`, `bidi_connection_close` (`use-live-agent.ts:331-530`).
- **M6.2 WebSocket event handling:** Satisfied. All expected event types are consumed.

### Audio pipeline

- **Microphone capture:** `MicCapture` in `frontend/src/lib/audio.ts:90-158`. Uses `AudioWorklet` with a 512-sample buffer, captures at 16 kHz mono PCM16, base64-encodes each chunk (`frontend/src/lib/audio.ts:110-143`).
- **Fallback resampling:** `downsample()` in `frontend/src/lib/audio.ts:53-70` performs box averaging, not naive decimation.
- **Playback:** `PcmPlayer` in `frontend/src/lib/audio.ts:160-226`. Schedules 24 kHz PCM16 buffers via WebAudio, creates the context on construction to avoid autoplay suspension, and flushes on interruption (`flush()` at `audio.ts:206-217`).
- **WAV export:** `pcm16ToWavBlob` wraps assistant audio for the per-turn replay player (`audio.ts:228-256`).
- **M6.2 audio formats:** Satisfied. 16 kHz PCM in, 24 kHz PCM out, interruption handling present.

### Camera control

- `CameraCapture` in `frontend/src/lib/camera.ts:8-148`. `start()` tries device-id, then preferred facing, then other facing, then any camera (`camera.ts:31-49`).
- Snap method captures JPEG base64 at 1024 max dimension, quality 0.7 (`camera.ts:63-75`).
- `record()` records a video clip with optional live mic track reuse, cloning the track to avoid iOS Safari silence (`camera.ts:88-136`).
- Agent-driven camera actions are handled in `use-live-agent.ts:419-444` for `control_camera` and `take_video` tools, and the `cameraControlRef` is registered at `use-live-agent.ts:729-737`.
- **M6.2 camera control:** Satisfied. Manual and agent-driven start/stop/snap/flip/record are present.

### Transcripts

- `appendText()` in `use-live-agent.ts:148-185` merges streaming text into messages and emits timed `LiveSegment` objects.
- `VoiceDock.tsx` renders segments with `Transcription` / `TranscriptionSegment` (`frontend/src/views/VoiceDock.tsx:183-205`).
- `Transcription` supports `onSeek` and active/past styling (`frontend/src/components/ai-elements/transcription.tsx:39-124`).

### Tool rendering

- `ChatThread.tsx` maps tool parts to `Tool`/`Sandbox`/`ChainOfThought` components (`frontend/src/views/ChatThread.tsx:141-458`).
- Tool parts from `tool_use_stream`/`tool_result` are upserted in `use-live-agent.ts:206-233` and `use-live-agent.ts:455-479`.
- **M6.2 tool rendering:** Satisfied. Tool names, inputs, outputs, and errors are rendered; shell tools get a special sandbox view.

### AI Elements usage

- `Conversation`, `Message`, `MessageResponse`, `ChainOfThought`, `Tool`, `Task`, `Plan`, `Sandbox`, `JSXPreview`, `AudioPlayer`, `Image`, `PromptInput`, `Queue`, `Transcription`, `ModelSelector`, `VoiceSelector`, `SpeechInput`, `Artifact`, `WebPreview`, `Canvas`/`Controls`/`Node`/`Edge`/`Connection`/`Panel` are all present in `frontend/src/components/ai-elements/`.
- They are built on top of `frontend/src/components/ui/*` primitives (shadcn/ui + Radix).

### Voice console gaps vs M7.4

| Requirement | Status | Evidence |
|---|---|---|
| `VoiceOrb` state machine | **Partial** | `StatusOrb` in `VoiceDock.tsx:48-61` is a CSS orb with `animate-pulse`; it is not a Rive/WebGL `VoiceOrb` and does not display a waveform. |
| Waveform | **Missing** | No audio-visualizer component. |
| Dual-role transcript | **Present** | `Transcription`/`TranscriptionSegment` in `VoiceDock.tsx:183-205`. |
| Tool/task activity | **Present** | `Tool`/`Task`/`ChainOfThought` in `ChatThread.tsx`. |
| Reasoning | **Present** | `thought` parts rendered in `AssistantChainOfThought` (`ChatThread.tsx:227-460`). |
| Photo cards | **Present** | `Image` component renders captured frames (`ChatThread.tsx:523-535`). |
| Quick replies | **Missing** | No suggestion chips. |
| Readiness meter | **Missing** | No per-property readiness/progress meter in the console. |
| Glove-friendly controls | **Missing** | Buttons are desktop-sized; no large tap targets or push-to-talk. |

---

## Mobile / PWA Readiness Audit

### PWA fundamentals

- **Manifest:** Not found in `frontend/public/` or `apps/web/`.
- **Service worker:** No `sw.ts`, no Serwist, no `navigator.serviceWorker.register()` call.
- **Viewport:** `frontend/index.html` was not audited; the only public asset is `public/inspection.html`, which has a proper viewport meta (`public/inspection.html:5`). The React app relies on Vite’s default `index.html`.
- **Installability:** Not implemented.

### Mobile-first layout

- `App.tsx` renders a desktop-style header + right sidebar (`VoiceDock`) + optional right `AgentPanel` (`frontend/src/App.tsx:24-107`).
- No mobile bottom navigation, no hamburger menu, no role-aware shell.
- `VoiceDock` has a fixed `w-80` width (`frontend/src/views/VoiceDock.tsx:68`), which would be unusable on a phone.
- `use-mobile.ts` exists (`frontend/src/hooks/use-mobile.ts:1-19`) but is **not used** anywhere in the app shell.

### Offline

- **IndexedDB queue:** Not implemented.
- **Sync-on-reconnect:** Not implemented.
- **Network assumption:** `use-live-agent.ts` and `InspectionView.tsx` call `/api/*` and `/ws` directly; there is no queue layer.
- M7.11 is **not started**.

---

## Design System Implementation Status

### `DESIGN.md` vs React app

`frontend/src/index.css` is the global stylesheet, but it does **not** implement `DESIGN.md`:

- It uses a generic shadcn blue/grey palette (`--primary: oklch(0.558 0.165 254)`) rather than the warm hospitality neutrals and forest green (`--primary: #17211d`, `--primary-container: #2c3632`) defined in `DESIGN.md`.
- Fonts are system sans-serif (`--font-sans: ui-sans-serif, system-ui, ...`) and `Geist Mono`; it does **not** import `Fraunces`, `EB Garamond`, or `Hanken Grotesk`.
- No `label-caps`, `display-lg`, `headline-lg`, etc. utility classes.
- Light/dark mode exists (`index.css:46-74`) but is driven by the `.dark` class, not by `prefers-color-scheme` alone.

### Where `DESIGN.md` is actually implemented

`public/inspection.html` hardcodes the hospitality palette and typography directly:

- CSS variables mirror `DESIGN.md` colors (`public/inspection.html:11-35`).
- Uses `EB Garamond` for headlines and `Hanken Grotesk` for body text (`public/inspection.html:9`, `public/inspection.html:41`).
- Implements the Property Header, glassmorphism progress bar, soft shadows, and pill-shaped sign-off button (`public/inspection.html:51-324`).
- This is the closest thing to the M7.2 design system, but it is isolated in a single static file.

### `apps/web` design system

- `apps/web/src/app/globals.css` defines only two colors and falls back to Arial. It does not implement `DESIGN.md`.

---

## Views / Components Coverage vs M7 Requirements

| M7 | Requirement | Status | Notes |
|---|---|---|---|
| M7.1 | Next.js App Router + TypeScript + Tailwind v4 + shadcn/ui + AI Elements | **Not started** | `apps/web` is a Next.js starter; AI Elements are not in `apps/web`. |
| M7.2 | `DESIGN.md` tokens, fonts, light/dark | **Not started in React/Next** | Implemented only in `public/inspection.html`. |
| M7.3 | App shell & navigation — role-aware, mobile bottom-nav, voice action, desktop sidebar | **Not started** | `frontend/App.tsx` is desktop-only and not role-aware. |
| M7.4 | Live Voice Console | **Partial** | Core BIDI session works; missing waveform, quick replies, readiness meter, glove controls. |
| M7.5 | Today / Daily Route | **Missing** | No task list, route, map, or arrival deadlines. |
| M7.6 | Property detail | **Missing** | Only hardcoded property header inside `public/inspection.html`. |
| M7.7 | Checklist / Inspection runner | **Partial** | `public/inspection.html` has a complete static checklist; `InspectionView.tsx` bridges it to the agent, but it is not a React/Next component. |
| M7.8 | Work Orders | **Missing** | No list, status pipeline, or detail view. |
| M7.9 | Report viewer | **Missing** | `inspection.html` can export itself as HTML, but no report viewer exists. |
| M7.10 | Camera capture | **Partial** | Camera capture and recording work in `use-live-agent.ts`/`camera.ts`, but no capture sheet, offline queue, or asset attachment. |
| M7.11 | PWA + offline | **Missing** | No manifest, service worker, IndexedDB, or sync strategy. |
| M7.12 | Ops dashboard | **Missing** | No portfolio readiness or exceptions view. |

---

## Offline / Camera Status

- **Camera:** Fully functional in the browser via `getUserMedia` (`camera.ts:24-60`), with device selection, facing-mode fallback, and video recording (`camera.ts:88-136`).
- **Offline queue:** Not implemented.
- **Inspection form persistence:** `public/inspection.html` exports its own state as a self-contained HTML file (`public/inspection.html:1076-1106`), but there is no IndexedDB queue or background sync.
- **Network-dependent paths:** `InspectionView.tsx` POSTs the snapshot to `/api/inspection/export` every 5 seconds (`InspectionView.tsx:226-255`), which will fail silently offline.

---

## Build Results and Errors

### `frontend/` build

```bash
cd /Users/tims-stuff/RandD/RandD/frontend && npm run build
```

**Result:** ✅ **Successful.** `tsc -b && vite build` completed with no TypeScript errors. The production bundle is in `frontend/dist/`.

Warnings observed:
- Rollup reported several chunks >500 kB after minification (notably the main index chunk at ~2.77 MB). This is expected from the large language/theme dependency tree (Shiki, Mermaid, Cytoscape, etc.) and is not a blocking error.
- No runtime errors or missing-dependency errors.

### `apps/web/` build

**Result:** Not run. `apps/web/node_modules` does not exist, so dependencies must be installed first. The package is the default Next.js starter and has no product code, so a build would only prove the starter template compiles. To avoid modifying the workspace, installation was not performed during this read-only audit.

---

## Risks and Recommendations

1. **Architecture risk:** The target PWA is supposed to be Next.js, but all working code is in a Vite demo. Recommendation: freeze the Vite demo as a BIDI reference, then port the relevant hooks/components into `apps/web` (or rebuild the product directly in `apps/web`).
2. **PWA / offline risk:** The platform’s NFRs require offline checklist/photo capture. Recommendation: add Serwist or Workbox, an `manifest.json`, and an IndexedDB/Dexie queue before any field pilot.
3. **Design-system drift:** `DESIGN.md` is only honored in the static HTML file. Recommendation: move the hospitality tokens into a Tailwind theme (e.g., `globals.css` in `apps/web`) and apply them to all AI Elements/shadcn components.
4. **Mobile UX risk:** The current layout is desktop-only. Recommendation: redesign the shell around a mobile bottom nav with a large voice action, responsive panels, and glove-friendly touch targets.
5. **Security risk:** Door codes and Wi-Fi passwords are shown in plaintext inside `public/inspection.html` (e.g., line 416 shows `Door Code: 4135`). This is acceptable for a demo but must be masked/revealed and encrypted before production (M1.6).
6. **AI Elements coupling:** The vendored components are in `frontend/src/components/ai-elements`. Recommendation: either install the official `ai-elements` package in `apps/web` or publish the vendored components to a shared package (`packages/ui`) so the Next.js app can consume them.
7. **Bundle size:** The Vite bundle is heavy because of Shiki/Mermaid. Recommendation: lazy-load language/theme assets in the Next.js app and use `next/dynamic` for heavy AI Elements.

---

## Requirement Mapping Checklist

### M7.1 — Next.js App Router scaffold
- [ ] `apps/web` contains the product pages.
- [ ] shadcn/ui installed in `apps/web`.
- [ ] AI Elements installed/imported in `apps/web`.

### M7.2 — Design system
- [ ] `DESIGN.md` colors applied in `apps/web/src/app/globals.css`.
- [ ] `Fraunces`/`EB Garamond` + `Hanken Grotesk`/`Geist` loaded.
- [ ] Light/dark mode implemented globally.

### M7.3 — App shell & navigation
- [ ] Role-aware routing.
- [ ] Mobile bottom navigation with prominent voice action.
- [ ] Desktop sidebar.

### M7.4 — Live Voice Console
- [x] BIDI WebSocket session (`use-live-agent.ts`).
- [x] Dual-role transcript (`VoiceDock.tsx`).
- [x] Tool/task activity (`ChatThread.tsx`).
- [x] Reasoning / chain-of-thought (`ChatThread.tsx`).
- [x] Photo cards (`Image` component).
- [ ] Waveform / animated `VoiceOrb`.
- [ ] Quick replies.
- [ ] Readiness meter.
- [ ] Glove-friendly controls.

### M7.5 — Today / Daily Route
- [ ] Task list grouped by geo/cluster.
- [ ] Map + directions.
- [ ] Arrival deadlines + stage chips.

### M7.6 — Property detail
- [ ] Spaces/assets/features.
- [ ] Masked credentials with reveal.
- [ ] Standing instructions, baseline photos, history.

### M7.7 — Checklist / Inspection runner
- [x] Static checklist form exists (`public/inspection.html`).
- [ ] React/Next checklist component.
- [ ] PASS/FAIL/NA support (currently only PASS via checkbox).
- [ ] Required-photo capture enforcement.
- [ ] Agent-assisted vs manual mode.

### M7.8 — Work Orders
- [ ] List + detail views.
- [ ] Status pipeline (NEW → ASSIGNED → IN_PROGRESS → BLOCKED → DONE → CANCELLED).
- [ ] Priority and before/after photos.

### M7.9 — Report viewer
- [ ] Embedded-photo report.
- [ ] Category summaries, repairs, sign-off action, delivery status.

### M7.10 — Camera capture
- [x] `getUserMedia` capture (`camera.ts`).
- [ ] Capture sheet.
- [ ] Offline queue.
- [ ] Attach to checklist/asset (partially wired via agent tools only).

### M7.11 — PWA + offline
- [ ] Web app manifest.
- [ ] Service worker (Serwist/Workbox).
- [ ] IndexedDB queue for checklist/photos.
- [ ] Sync-on-reconnect.

### M7.12 — Ops dashboard
- [ ] Portfolio readiness view.
- [ ] Pipeline and exceptions.

### M6.2 — Realtime transport details
- [x] WebSocket event handling (`use-live-agent.ts:331-530`).
- [x] Audio in 16 kHz PCM, out 24 kHz PCM (`audio.ts`).
- [x] Camera control (`camera.ts`, `use-live-agent.ts:419-444`).
- [x] Tool rendering (`ChatThread.tsx`, `tool.tsx`, `sandbox.tsx`).
