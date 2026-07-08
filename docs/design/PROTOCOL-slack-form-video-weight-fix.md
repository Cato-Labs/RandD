# Protocol — Keep Slack Inspection Forms Lightweight (Video Fix)

**Status:** Ready to implement · **Date:** 2026-07-08
**Audience:** the code agent editing `frontend/public/inspection.html`.
**Goal:** Stop user-uploaded videos from being base64-inlined (uncompressed) into the exported form. Route them through the **existing** compress-and-serve endpoint so the Slack form stays small — exactly like agent-captured videos already do.
**Guiding principle:** Do the *least* change. Make the user-upload path match the agent path that already works. Do not invent a new mechanism.

---

## 1. The problem (verified)

- **Agent-captured videos are already lightweight.** Path: `recordClip()` → `POST /api/inspection/video` → backend `compress_clip()` → returns a `/workspace/…` URL → `setSectionVideo(url)`. The form stores a **short URL string**, not the video bytes. (`use-live-agent.ts:recordClip`, `backend/app/main.py:41-89`, `InspectionView.tsx:163`.)
- **User-uploaded videos are NOT.** In `inspection.html` the file `change` handler does `URL.createObjectURL(f)` and stores that blob URL (lines ~994-999). At export, `toDataUrl` fetches the blob and `readAsDataURL`s it into **base64 with no compression and no size cap** (the image-compression branch only handles `data:image/`; video falls through to the raw path). A single clip can add **megabytes** to the exported HTML that ships to Slack.
- Evidence it's a known pain: the uncommitted diff raised nginx `client_max_body_size` to `100M` — tolerating huge exports instead of preventing them.

**Fix in one sentence:** when a user picks a video file, upload it to `/api/inspection/video` (same endpoint the agent uses) and store the returned `/workspace/…` URL — never a blob URL, never base64.

---

## 2. Scope — one file, three small edits

Edit **only** `frontend/public/inspection.html`. No backend change (the endpoint already exists and already compresses). No new dependencies.

### Edit 1 — User video upload uses the compress endpoint (the core fix)

Find the video file-input `change` handler (currently around line 994):

```js
vinput.addEventListener('change', function(){
  const f = vinput.files && vinput.files[0];
  if(!f) return;
  const url = URL.createObjectURL(f);
  setVideo(url, 'user', url);
  vinput.value = '';
});
```

Replace its body so the file is uploaded and the returned workspace URL is used. Keep it simple and defensive (fall back to the old local-preview behavior only if the upload fails, so offline use still shows *something*):

```js
vinput.addEventListener('change', function(){
  const f = vinput.files && vinput.files[0];
  if(!f) return;
  vinput.value = '';
  // Show an instant local preview while the upload runs.
  const localUrl = URL.createObjectURL(f);
  setVideo(localUrl, 'user', localUrl);
  // Upload to the SAME endpoint the agent uses; it compresses server-side and
  // returns a small /workspace/... URL. Swap the preview for that URL so the
  // exported form embeds a short link, never the raw video bytes.
  const section = card.dataset.id || '';
  fetch('/api/inspection/video?section=' + encodeURIComponent(section) + '&duration=0', {
    method: 'POST',
    headers: { 'Content-Type': f.type || 'video/webm' },
    body: f
  })
  .then(function(r){ return r.json(); })
  .then(function(info){
    if (info && info.url) {
      // Replaces the blob preview; setVideo revokes the old objectUrl.
      setVideo(info.url, 'user');
      update();
    }
  })
  .catch(function(){ /* keep the local preview; offline/degraded is acceptable */ });
});
```

Notes:
- `setVideo(src, source, objectUrl)` already revokes a prior `objectUrl` (line ~969), so swapping preview → workspace URL cleans up the blob automatically.
- `update()` after the swap persists the small URL into form state.
- The endpoint returns `{ url: "/workspace/captures/…", … }` (verified in `backend/app/main.py:75-89`).

### Edit 2 — Stop `toDataUrl` from ever inlining videos

In `exportHtml`'s `toDataUrl`, the video-bloat comes from the generic `blob → base64` fallback. Videos should now always be `/workspace/…` URLs (Edit 1), so **leave them as URLs** in the export instead of base64-embedding.

Change the section-video baking loop (currently ~line 1515):

```js
for(const s of state.sections){
  if(s.video) s.video.src = await toDataUrl(s.video.src);
}
```

to:

```js
for(const s of state.sections){
  // Videos stay as /workspace/... URLs — never base64-embedded (keeps the
  // export small). Only leftover blob: previews (failed upload) are dropped
  // so the exported file never carries raw video bytes.
  if(s.video && s.video.src && s.video.src.indexOf('blob:') === 0){
    s.video.src = null;
  }
}
```

This guarantees the exported HTML contains at most a short URL per video, never megabytes of base64. (Images still go through `toDataUrl` unchanged — they must be embedded so the form is self-contained; they’re already capped at 640px / q0.4.)

### Edit 3 (optional, readability only) — flatten `toDataUrl`'s self-recursion

`toDataUrl` currently calls itself after converting a fetched blob to base64. Since videos no longer reach it (Edit 2 handles them before the loop, and only images are passed), you may simplify: the function now only ever receives image `src` values (data URLs or image blob URLs). If you keep it generic, leave it; if you simplify, ensure the "compress if >640px" image branch is the single code path. **Do not** change image behavior — only remove the now-dead video fallback complexity. Skip this edit if unsure; Edits 1–2 are sufficient.

---

## 3. Explicit DO-NOT (disruption guards)

1. **Do not** touch the agent video path (`recordClip`, `setSectionVideo`, `/api/inspection/video` handler) — it already works and is the model we're copying.
2. **Do not** change image compaction (640px / JPEG q0.4, the no-double-compress `<=640` guard). Images must stay embedded and self-contained.
3. **Do not** base64-embed videos under any circumstance.
4. **Do not** revert the `client_max_body_size 100M` line yet — leave it as a safety margin; it becomes harmless once videos are URLs.
5. **Do not** alter `getState()` field shapes, the `formId`/UUID logic, rehydration, or the `postMessage('qc-form-changed')` sync — those are correct.
6. **Do not** add libraries. This is pure vanilla JS in one file.

---

## 4. Verification (must pass before commit)

1. **User video → workspace URL, not base64.**
   - Open the inspection form, upload a video to a section.
   - After the upload resolves, `window.qcInspection.getState().sections[…].video.src` must start with `/workspace/` (not `blob:` and not `data:`).
2. **Export size is small.**
   - Call `await window.qcInspection.exportHtml()`; confirm the returned HTML does **not** contain `data:video` and does not contain any `blob:` URL.
   - Sanity: with one video + a few photos, exported size should be tens/low-hundreds of KB (photos only), not multiple MB.
3. **Everything else still persists (regression):** house name, inspector, signature, item photos, item notes, section notes, repairs, temp all still present in `getState()` and survive a rehydrate (reopen the exported HTML).
4. **Agent video path unaffected:** an agent `take_video` still lands in the correct section as a `/workspace/…` URL.
5. **Offline/degraded path:** if `/api/inspection/video` fails, the local preview still shows in-session; the export simply drops the blob (no crash, no raw bytes).

---

## 5. Definition of done

- User-uploaded and agent-captured videos both stored as `/workspace/…` URLs.
- Exported HTML never contains `data:video` or `blob:`.
- Images unchanged (embedded, ≤640px, q0.4, no double-compression).
- All A-fields (photos, videos, notes, house, inspector, signature) still persist and rehydrate.
- One file changed (`inspection.html`); no backend, no deps, no behavior removed.

---

## Appendix — Why this is the simplest correct fix
- The compress-and-serve endpoint **already exists and is already used** by the agent path; we reuse it instead of adding client-side video compression (which is heavy and unreliable in-browser).
- Videos become short strings → the export is dominated only by already-compacted images.
- The change is localized to the one handler that was inconsistent, making both video sources use one strategy — lighter (B) and simpler/uniform (C).
