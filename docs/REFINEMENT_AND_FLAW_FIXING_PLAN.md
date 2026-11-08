# VoiceRep: Engineering Refinement & Flaw-Fixing Master Plan

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Target Branch:** `feature/self-hosted-voice-cloning`  
**Focus:** Reliability, Concurrency, Hardening, and Flaw Resolution (Over Feature Bloat)

---

## 1. Executive Strategy & Market Intelligence

### 1.1 The VoiceStudio Benchmark
Following an in-depth analysis of [VoiceStudio](https://voicestudio.sh/) and its open-source repository ([`debpalash/VoiceStudio`](https://github.com/debpalash/VoiceStudio), 102k+ stars, #1 GitHub Trending), one engineering tenet stands out above all others (documented in creator Palash Deb's `CLAUDE.md`):

> **"A first-run that actually works. Fix issues properly and future-proof the whole class of bug. Never commit half-working code."**

VoiceStudio achieved explosive adoption not by having 50 fragile features, but by providing an unshakeable, zero-cloud-cost local cloning engine that installs easily and does not crash when stressed.

### 1.2 VoiceStudio vs. VoiceRep: Architectural Moat & Positioning

| Dimension | VoiceStudio (`debpalash/VoiceStudio`) | VoiceRep (`VoiceRep`) |
| :--- | :--- | :--- |
| **Primary Nature** | Local desktop Electron app (single-user workstation) | Full-stack Web & API Platform (SaaS-ready, multi-tenant) |
| **Voice Cloning Engine** | Multi-engine sidecars (OmniVoice, CosyVoice, F5-TTS, MeloTTS) | Dual-Provider Abstraction: Self-Hosted F5-TTS + ElevenLabs fallback |
| **Real-time Voice Agents** | None (focused on text-to-speech studio generation & video dubbing) | **Native Conversational Voice Agents** (bidirectional low-latency WebSockets) |
| **API & Developer Access** | Local server mode via FastAPI | Production REST API with Bearer token authentication & per-user tenancy |
| **Infrastructure Cost** | $0.00 (Inference runs on the user's local machine) | $0.00 local/MPS mode + Serverless GPU scale-to-zero ready |
| **Current Priority** | Ecosystem integrations & GUI polish | **Hardening existing capabilities, eliminating crashes, and audio reliability** |

VoiceRep's competitive advantage is **interactive conversational voice agents combined with self-hosted zero-cost voice cloning**. However, to ship VoiceRep as a viable, dependable product, we must fix the 5 critical engineering flaws and bottlenecks identified during our codebase audit.

---

## 2. Deep Codebase Audit: Identified Flaws & Bottlenecks

```
                                CRITICAL FLAWS IDENTIFIED
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. CONCURRENCY: Unprotected GPU inference causes MPS/CUDA crashes under parallel load   │
 │ 2. SEQUENCE LENGTH: F5-TTS DiT cross-attention truncates or hallucinates on text >50 w │
 │ 3. WEBSOCKET PIPELINE: Agent playground mic stream is unhooked to backend Whisper ASR   │
 │ 4. SECURITY: Storage download endpoint vulnerable to path traversal (../../)            │
 │ 5. USER EXPERIENCE: Modal recommends 60-120s but FFmpeg clips 12s; no in-app mic record │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔴 Flaw 1: Unprotected Concurrent GPU Inference (Race Condition & VRAM Crash)
* **Location:** [`backend/app/providers/self_hosted.py#L330-L343`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/backend/app/providers/self_hosted.py#L330-L343)
* **Root Cause:**
  ```python
  async def synthesize(self, voice_id: str, text: str, settings: dict[str, Any], model_id: str = "f5_tts") -> bytes:
      return await asyncio.to_thread(self._synthesize_sync, voice_id, text, settings, model_id)
  ```
  While an `_engine_lock` guards the initial *loading* of model weights into memory, there is **no semaphore or lock guarding `engine.infer()` during execution**.
* **Failure Mode:**
  If two users generate audio simultaneously, or if an agent generates speech while a studio generation is running, multiple OS threads execute `engine.infer()` concurrently against the same PyTorch model instance.
  * **On Apple Silicon (`mps`):** Triggers `MPS internal error: encoder is already in use` or corrupted output tensors.
  * **On NVIDIA CUDA:** Triggers immediate `CUDA out of memory` or driver segfaults.
* **The Refinement:**
  Add an `asyncio.Semaphore(1)` inference barrier in `SelfHostedProvider`. Requests queue cleanly into a FIFO buffer, guaranteeing thread-safe, sequential GPU execution without crashing.

---

### 🔴 Flaw 2: Cross-Attention Sequence Window Limit on Long Text (Audio Truncation)
* **Location:** [`backend/app/providers/self_hosted.py#L267-L295`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/backend/app/providers/self_hosted.py#L267-L295)
* **Root Cause:**
  Conditional Flow Matching Diffusion Transformers (F5-TTS DiT) operate on a fixed cross-attention context window designed for **up to 25–30 seconds of speech (approx. 45–55 words)**.
* **Failure Mode:**
  When a user pastes a paragraph (>50 words) into the Studio:
  * The ODE solver either truncates the output mid-sentence.
  * Or the cross-attention matrix destabilizes, causing acoustic babble, clicks, or silence at the tail.
* **The Refinement:**
  Implement an intelligent **phonetic sentence-boundary chunker** (`re.split(r'(?<=[.?!;:\n])\s+', text)`). Texts longer than 180–200 characters are split into natural clauses, synthesized sequentially through the cached reference prompt, and seamlessly stitched with 150ms natural silence padding into a single output audio file.

---

### 🔴 Flaw 3: Disconnected Audio Stream in Agent WebSocket Playground
* **Location:** 
  * [`frontend/app/agents/[id]/playground/page.tsx#L76-L86`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/frontend/app/agents/[id]/playground/page.tsx#L76-L86)
  * [`backend/app/api/v1/agents.py#L166-L169`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/backend/app/api/v1/agents.py#L166-L169)
* **Root Cause:**
  * In the frontend playground, `navigator.mediaDevices.getUserMedia` acquires the microphone stream, but **no `AudioWorkletNode` or `MediaRecorder` captures and emits PCM chunks** through the WebSocket.
  * In the backend WebSocket handler (`/agents/ws/{session_id}`), binary frames are unhandled:
    ```python
    elif "bytes" in msg and msg["bytes"]:
        # Binary audio frame received from user microphone
        pass
    ```
* **Failure Mode:**
  The playground displays an active visualizer ("Listening..."), but voice audio never reaches the backend. The agent never responds to voice input, breaking the core promise of an interactive voice agent.
* **The Refinement:**
  1. Add a standard Web Audio 16kHz mono capture pipeline in the frontend playground that transmits PCM/WebM audio chunks over the WebSocket.
  2. In the backend, transcribe chunks using `whisper-tiny` upon detecting a speech pause, route text to the agent LLM prompt, generate an answer, synthesize using `self_hosted_provider.synthesize()`, and stream base64 audio frames back to the client.

---

### 🔴 Flaw 4: Path Traversal Vulnerability in Local Storage API
* **Location:** [`backend/app/api/v1/storage.py#L9-L26`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/backend/app/api/v1/storage.py#L9-L26)
* **Root Cause:**
  ```python
  @router.get("/download/{file_path:path}")
  async def download_local_file(file_path: str):
      dest = os.path.join(os.path.abspath(settings.LOCAL_STORAGE_PATH), file_path)
      if not os.path.exists(dest):
          raise HTTPException(status_code=404, detail="File not found")
      return FileResponse(dest)
  ```
  `os.path.join` does not block directory traversal sequences (e.g. `../../app/core/config.py` or `../../../../etc/passwd`).
* **Failure Mode:**
  Any unauthenticated client can retrieve sensitive backend files or environment secrets. Furthermore, standard `FileResponse` without byte-range headers causes the frontend `<audio>` scrubber to reset to 0:00 when clicked.
* **The Refinement:**
  * Enforce strict `os.path.commonpath` verification to guarantee resolution inside `LOCAL_STORAGE_PATH`.
  * Ensure full HTTP 206 Partial Content (`Range: bytes=`) support for seamless audio scrubbing.

---

### 🔴 Flaw 5: UX Mismatch & Missing In-Browser Mic Recording
* **Location:** [`frontend/components/voices/CreateVoiceModal.tsx#L173`](file:///Users/yashchaurasia/Desktop/Code/VoiceRep/frontend/components/voices/CreateVoiceModal.tsx#L173)
* **Root Cause:**
  * The modal copy states: *"Upload 1-3 clear audio samples (60-120 seconds recommended)"*.
  * In reality, the backend preprocessing pipeline (`self_hosted.py#L122`) strictly clips the audio to the first 12 seconds:
    ```bash
    ffmpeg -y -i input.wav -ss 0 -t 12 -ar 24000 -ac 1 output.wav
    ```
  * If a user uploads a 2-minute file where they hesitate, cough, or remain silent for the first 8 seconds, the reference prompt captures junk acoustics, leading to completely degraded voice cloning.
  * In addition, users must record audio externally, save a file, and manually upload it.
* **Failure Mode:**
  Users follow the UI prompt, upload long clips, get poor cloning results, and churn.
* **The Refinement:**
  * Correct the UI instruction to: *"Upload or record a clean 6–12 second sample. Speak naturally with minimal background noise."*
  * Add a native **"Record with Microphone"** tab in `CreateVoiceModal` with a 10-second prompt script, countdown timer, and playback preview before submission.

---

## 3. The 5-Step Refinement & Flaw-Fixing Roadmap

```
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ STEP 1: Inference Hardening & Long-Text Phonetic Chunking                               │
 │ • GPU inference lock (`asyncio.Semaphore(1)`) to eliminate concurrency crashes          │
 │ • Sentence-boundary text chunker with audio concatenation for long text (>180 chars)    │
 │ • Model pre-warming on FastAPI lifespan startup to eliminate 10s cold-start             │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ STEP 2: Storage Security & Audio Range Scrubbing                                        │
 │ • Directory traversal protection (`commonpath` verification)                            │
 │ • HTTP 206 Partial Content / `Range: bytes=` support for smooth audio scrubbing         │
 │ • Ephemeral temp files cleanup handler on startup/shutdown                              │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ STEP 3: Voice Cloning Modal Refinement & In-Browser Recording                           │
 │ • In-modal Web Audio recorder (record 10s reference sample directly via microphone)     │
 │ • Reference sample audio player preview before submission                               │
 │ • Correct UI guidance to prime 6–12s speech window                                      │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ STEP 4: Conversational WebSocket Full-Duplex Pipeline                                   │
 │ • Wire microphone PCM audio streamer in Agent Playground                                │
 │ • Decode incoming audio frames on backend via Whisper ASR                               │
 │ • Synthesize & stream back audio packets matching ConvAI client protocol                │
 └────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
 ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
 │ STEP 5: Verification & Zero-Cost Turnkey Packaging                                      │
 │ • Add end-to-end integration tests for long text, concurrency, and path traversal       │
 │ • Provide a turnkey `docker-compose.yml` & `run-local.sh` for 1-click startup           │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Engineering Specifications for Each Step

### 4.1 Step 1: Inference Hardening & Long-Text Chunking
**Files to Modify:**
- `backend/app/providers/self_hosted.py`
- `backend/app/main.py`

#### Implementation Details:
1. **Async Semaphore Barrier:**
   In `SelfHostedProvider.__init__`, initialize:
   ```python
   self._infer_semaphore = asyncio.Semaphore(1)
   ```
   Wrap the public `synthesize()` entrypoint:
   ```python
   async def synthesize(self, voice_id: str, text: str, settings: dict[str, Any], model_id: str = "f5_tts") -> bytes:
       async with self._infer_semaphore:
           return await asyncio.to_thread(self._synthesize_sync, voice_id, text, settings, model_id)
   ```

2. **Phonetic Sentence Chunking & Stitching:**
   In `_synthesize_sync`:
   - If `len(text) <= 180`, run single-pass inference.
   - If `len(text) > 180`, split using regex pattern `r'(?<=[.?!;:\n])\s+'`.
   - Iterate through chunks, generating audio per chunk.
   - Create a 150ms silence array (`np.zeros(int(sample_rate * 0.15), dtype=np.float32)`).
   - Concatenate all arrays: `np.concatenate([c1, silence, c2, silence, ...])`.
   - Export once as high-bitrate MP3 via `soundfile` / `pydub`.

3. **FastAPI Lifespan Model Pre-Warming:**
   In `backend/app/main.py`:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Pre-warm F5-TTS and Whisper models on startup in background thread
       if settings.DEFAULT_VOICE_PROVIDER == "self_hosted":
           asyncio.create_task(prewarm_self_hosted_engine())
       yield
   ```

---

### 4.2 Step 2: Storage Security & Audio Scrubbing
**Files to Modify:**
- `backend/app/api/v1/storage.py`
- `frontend/components/audio/AudioPlayer.tsx`

#### Implementation Details:
1. **Directory Traversal Guard:**
   Implement strict verification:
   ```python
   def get_safe_storage_path(base_dir: str, rel_path: str) -> str:
       full_path = os.path.abspath(os.path.join(base_dir, rel_path.lstrip("/")))
       base_abs = os.path.abspath(base_dir)
       if os.path.commonpath([full_path, base_abs]) != base_abs:
           raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
       if not os.path.exists(full_path):
           raise HTTPException(status_code=404, detail="File not found")
       return full_path
   ```

2. **HTTP 206 Partial Content (Byte Range Support):**
   Ensure Starlette/FastAPI `FileResponse` serves `Accept-Ranges: bytes` so that moving the seek bar in the frontend audio player scrubs cleanly without restarting audio.

---

### 4.3 Step 3: Voice Cloning Modal UX & In-Browser Recording
**Files to Modify:**
- `frontend/components/voices/CreateVoiceModal.tsx`

#### Implementation Details:
1. **Dual Tab Selector:**
   Provide two intuitive modes:
   * **Tab 1: Upload File** (existing drag & drop for WAV/MP3)
   * **Tab 2: Record Voice** (in-browser recording)

2. **In-Browser Recording Component:**
   * Script to read: *"I authorize VoiceRep to clone my voice for personalized speech synthesis."*
   * 10-second visual progress bar with countdown.
   * Auto-stops at 10 seconds.
   * Built-in playback button so the user can verify sample clarity before clicking "Create Voice".
   * Directly attaches the recorded `Blob` (`audio/wav`) to the form payload.

3. **Accurate User Guidance:**
   Update helper text to clarify that a clean, background-noise-free 6–12 second sample yields the highest voice similarity in Diffusion Transformer models.

---

### 4.4 Step 4: Conversational WebSocket Full-Duplex Pipeline
**Files to Modify:**
- `frontend/app/agents/[id]/playground/page.tsx`
- `backend/app/api/v1/agents.py`

#### Implementation Details:
1. **Frontend Web Audio Capture:**
   * Utilize `MediaRecorder` or `AudioContext` to package 16kHz mono audio into chunks (e.g. 500ms slices).
   * Emit frames over the active WebSocket:
     ```typescript
     ws.send(JSON.stringify({ type: "audio_chunk", data: base64Audio }));
     ```

2. **Backend Audio Handling & Agent Loop:**
   * In `backend/app/api/v1/agents.py`:
     - Accumulate audio frames in session buffer.
     - On silence/turn-completion signal, run `whisper-tiny` transcription.
     - Append transcription to agent conversation memory.
     - Generate LLM agent reply.
     - Synthesize reply audio via `self_hosted_provider.synthesize()`.
     - Stream audio packets back:
       ```python
       await websocket.send_json({
           "type": "audio",
           "audio_event": {"audio_base_64": base64_audio}
       })
       ```

---

### 4.5 Step 5: Automated Verification & Turnkey Local Packaging
**Files to Create/Modify:**
- `backend/tests/test_self_hosted_provider.py`
- `run-local.sh`

#### Implementation Details:
1. **Automated Stress Tests:**
   * **Test 1: Concurrency Race Condition Guard**: Run 3 parallel `asyncio.gather(synthesize(), synthesize(), synthesize())` and verify all complete successfully with distinct outputs.
   * **Test 2: Long-Text Chunking**: Pass a 600-character text and verify the output is a continuous, valid audio file with duration matching length.
   * **Test 3: Security Path Traversal Guard**: Attempt `GET /api/v1/storage/download/../../app/core/config.py` and verify HTTP 403 Forbidden is returned.

2. **Turnkey Local Startup Script (`run-local.sh`):**
   A unified shell script that:
   * Checks for conda/virtualenv environment with Python 3.11+.
   * Verifies PostgreSQL and Redis services.
   * Applies Alembic migrations (`alembic upgrade head`).
   * Boots the FastAPI backend on `:8000`.
   * Boots the Next.js frontend on `:3000`.
   * Displays clear URLs and health status in the terminal.

---

## 5. Verification Checklist

Before releasing any changes or marking steps complete, the following battery of tests must pass:

- [ ] `pytest backend/tests` passes 100% of test suites.
- [ ] Concurrent generation does not trigger `MPS internal error` on macOS Apple Silicon.
- [ ] Texts over 50 words synthesize completely without audio cutoff.
- [ ] Storage API blocks `../` path traversal attempts.
- [ ] Audio player scrub bar seeks forward and backward without playback reset.
- [ ] In-browser recording successfully captures a 10s WAV file and generates a cloned voice.
- [ ] Agent playground microphone input is received, transcribed, and answered with synthesized voice.
- [ ] `npm run build` in `frontend/` compiles with 0 type errors.

---

## 6. Document History

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| Nov 7, 2026 | 1.0.0 | Initial comprehensive refinement plan following VoiceStudio research & codebase audit | VoiceRep Core Team |
