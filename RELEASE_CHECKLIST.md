# Local release checklist

Audit date: 2026-11-11. Target: users install and run KolRep on their own trusted machine. Current decision: **hold the stable release** until the open gates below are completed. Changes are local and have not been committed, pushed, or published.

## Automated evidence

- [x] Initial production frontend build passed, including TypeScript.
- [x] Existing backend suite: 23 passed in the installed Python 3.11 `kolrep` environment.
- [x] Added regression checks for fixed local identity, blocked key reads/writes, symlink escapes, upload limits, audio tampering, and untrusted signers.
- [x] Final checks after release changes: backend 28 passed (one existing Starlette deprecation warning); frontend production build and TypeScript passed; shell syntax, Compose YAML/loopback assertions, and `git diff --check` passed. Compose runtime was not exercised.
- [ ] Frontend lint clean. Baseline: 36 errors, 14 warnings (explicit `any`, hook order/lifecycle, ref access, purity). Fix the source rather than disabling the rules.
- [ ] Pin/lock and validate Python dependencies on supported clean environments. Current requirements use lower bounds; installed-environment success does not establish reproducible installation.
- [ ] Validate a fresh `npm ci` installation, not only existing `node_modules`.

## Changes made during this audit

- Local owner identity cannot be selected through unsigned bearer claims.
- Media endpoints block signing keys/private metadata, including symlink paths; uploads and verifier reads enforce the configured file limit.
- Signing keys respect `LOCAL_STORAGE_PATH`; new private key files are created with owner-only permissions.
- Verification checks both audio content binding and the local signing certificate; acoustic detection alone does not establish authenticity.
- Removed unsupported legal compliance guarantees from generated claims and public-facing documentation/UI.
- Added dependency setup and fail-fast startup scripts; native listeners bind to loopback and child processes stop together.
- Compose publishes services on loopback, migrates before API startup, persists model cache, and excludes personal files from Docker builds.
- Removed the unused worker from the default stack: generation currently runs through the API, not a queued job.

## Fresh install acceptance (release gates)

Use a clean checkout and a new data directory/database. Do not test migrations against your only copy of personal data.

- [ ] Run `./setup-local.sh` successfully with Python 3.11, Node 22+, and FFmpeg.
- [ ] Run `./run-local.sh` with PostgreSQL/Redis already running; repeat using Compose-provided database/cache.
- [ ] Confirm startup on an empty PostgreSQL database reaches Alembic head. Restart and confirm repeat migration succeeds.
- [ ] Build/start the full Docker stack on a clean host. Confirm CPU inference and persistent model cache after restart.
- [ ] Confirm only loopback listeners on ports 3000/8000/5432/6379.
- [ ] Confirm missing dependencies, occupied app ports, invalid DB URL, and unavailable Redis fail with useful output and no orphan app processes.
- [ ] Open Studio, record a microphone sample with permission, create an authorized voice, generate short text and a long paragraph, seek/play/download audio, inspect history, and delete test records.
- [ ] Test denied microphone access, invalid/empty/oversized uploads, and generation failure recovery.
- [ ] Verify fresh MP3 and WAV signatures. Change audio bytes while retaining metadata and confirm rejection. Test an unknown installation's certificate and confirm it is not trusted locally.
- [ ] Restart the app and verify that voice profiles, generation history, downloaded media, and signing identity remain usable.
- [ ] After all models have loaded, set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, disconnect network access, restart, and repeat clone/generation/playback/verification. Inspect network activity to substantiate offline claims.
- [ ] Export database plus storage, restore into an isolated install, and repeat playback/verification. Validate the equivalent Compose volume restore.
- [ ] Record supported hardware, OS, memory requirements, model download size, and measured generation latency. Native Apple MPS, Linux CUDA, and CPU require separate evidence.

## Release packaging

- [ ] Include AGPL license and upstream model license/attribution links. The default F5-TTS weights are CC-BY-NC-4.0: https://huggingface.co/SWivid/F5-TTS . Do not describe the default model as unrestricted commercial software.
- [ ] Keep Agents and unvalidated C2PA interoperability out of stable release promises.
- [ ] Inspect the archive/image: no `.env`, personal samples, generated audio, database dumps, private signing keys, `node_modules`, or local virtual environment.
- [ ] Review the patch, commit it, and rerun automated gates at the exact release commit.
- [ ] Tag a preview release first, include known limitations and installation instructions, and collect fresh-machine reports before declaring stable support.

No public hosting configuration is included. There is no multi-user authentication boundary in local mode.
