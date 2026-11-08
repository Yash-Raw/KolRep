import asyncio
import json
import logging
import os
import random
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Optional

import numpy as np
import soundfile as sf
import torch

from app.core.config import settings
from app.providers.base import VoiceProvider
from app.services.audio_service import FFMPEG_BIN

logger = logging.getLogger("voicerep.self_hosted")

# Ensure Conda env binary directory is on PATH for transformers and child processes
CONDA_BIN = str(Path(FFMPEG_BIN).parent)
if CONDA_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{CONDA_BIN}:{os.environ.get('PATH', '')}"


def normalize_speech_text(text: str) -> str:
    """
    Normalizes numbers, currency, abbreviations, and punctuation to ensure
    precise phoneme generation and natural cadence.
    """
    if not text:
        return ""
    t = text.strip()

    # Currencies
    t = re.sub(r"\$(\d+(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"€(\d+(?:\.\d+)?)", r"\1 euros", t)
    t = re.sub(r"£(\d+(?:\.\d+)?)", r"\1 pounds", t)

    # Percentage and symbols
    t = re.sub(r"(\d+)\s*%", r"\1 percent", t)
    t = t.replace("&", " and ")
    t = t.replace("@", " at ")

    # Expand common abbreviations
    abbrevs = {
        r"\be\.g\.\b|\be\.g\b": "for example",
        r"\bi\.e\.\b|\bi\.e\b": "that is",
        r"\bvs\b\.?": "versus",
        r"\bapprox\b\.?": "approximately",
        r"\bDr\b\.?": "Doctor",
        r"\bMr\b\.?": "Mister",
        r"\bMrs\b\.?": "Missus",
        r"\bMs\b\.?": "Mizz",
        r"\bAI\b": "A I",
    }
    for pat, rep in abbrevs.items():
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # Ensure natural sentence punctuation
    if t and t[-1] not in ".!?:;":
        t += "."

    # Collapse multiple whitespaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def chunk_text_by_sentence(text: str, max_chars: int = 180) -> list[str]:
    """
    Splits text along sentence and clause boundaries (punctuation: . ! ? ; : \n),
    grouping small clauses together up to max_chars so each chunk is a natural,
    well-formed prosodic clause suitable for F5-TTS Diffusion Transformer attention windows.
    """
    if not text:
        return []
    
    # Split on sentence terminals while keeping punctuation attached
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.?!;:\n])\s+', text) if s.strip()]
    if not raw_sentences:
        return [text]

    chunks: list[str] = []
    current_chunk = ""

    for s in raw_sentences:
        if not current_chunk:
            current_chunk = s
        elif len(current_chunk) + len(s) + 1 <= max_chars:
            current_chunk += " " + s
        else:
            chunks.append(current_chunk)
            current_chunk = s

    if current_chunk:
        chunks.append(current_chunk)

    # In case any single sentence is longer than max_chars, split on commas or spaces
    final_chunks: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final_chunks.append(c)
        else:
            parts = [p.strip() for p in re.split(r'(?<=[,])\s+', c) if p.strip()]
            curr_part = ""
            for p in parts:
                if not curr_part:
                    curr_part = p
                elif len(curr_part) + len(p) + 1 <= max_chars:
                    curr_part += " " + p
                else:
                    final_chunks.append(curr_part)
                    curr_part = p
            if curr_part:
                final_chunks.append(curr_part)

    return final_chunks if final_chunks else [text]


class SelfHostedProvider(VoiceProvider):
    def __init__(self) -> None:
        self._engine: Any = None
        self._engine_lock = asyncio.Lock()
        self._infer_semaphore: Optional[asyncio.Semaphore] = None
        self._asr_pipeline: Any = None
        self._asr_lock = asyncio.Lock()
        self.storage_dir = Path(settings.SELF_HOSTED_VOICE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @property
    def infer_semaphore(self) -> asyncio.Semaphore:
        if self._infer_semaphore is None:
            self._infer_semaphore = asyncio.Semaphore(1)
        return self._infer_semaphore

    def _get_device(self) -> str:
        cfg_dev = settings.SELF_HOSTED_DEVICE.lower()
        if cfg_dev != "auto":
            return cfg_dev
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_engine_sync(self) -> Any:
        if self._engine is not None:
            return self._engine
        
        logger.info("Initializing Self-Hosted F5-TTS Engine...")
        from f5_tts.api import F5TTS

        device = self._get_device()
        logger.info(f"Loading F5TTS ({settings.SELF_HOSTED_MODEL}) on device: {device}")
        
        engine = F5TTS(
            model=settings.SELF_HOSTED_MODEL,
            device=device,
        )
        self._engine = engine
        logger.info("Self-Hosted F5-TTS Engine initialized successfully.")
        return self._engine

    async def get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        async with self._engine_lock:
            if self._engine is None:
                return await asyncio.to_thread(self._load_engine_sync)
            return self._engine

    def _load_asr_sync(self) -> Any:
        if self._asr_pipeline is not None:
            return self._asr_pipeline
        from transformers import pipeline
        logger.info("Loading Whisper ASR pipeline for reference audio transcription...")
        pipe = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device="cpu")
        self._asr_pipeline = pipe
        return self._asr_pipeline

    async def get_asr_pipeline(self) -> Any:
        if self._asr_pipeline is not None:
            return self._asr_pipeline
        async with self._asr_lock:
            if self._asr_pipeline is None:
                return await asyncio.to_thread(self._load_asr_sync)
            return self._asr_pipeline

    def _prepare_reference_audio(self, raw_audio_path: str, target_wav_path: str) -> None:
        """
        Cleans leading/trailing dead silence, limits duration to prime 12s speech chunk,
        and resamples to 24000 Hz mono 16-bit PCM WAV (F5-TTS native frequency).
        """
        cmd = [
            FFMPEG_BIN,
            "-y",
            "-i", raw_audio_path,
            "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB:detection=peak,aformat=sample_fmts=s16:sample_rates=24000:channel_layouts=mono",
            "-t", "12",
            target_wav_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.warning(f"Audio cleaning filter warning, falling back to direct wav convert: {res.stderr.decode()}")
            fallback_cmd = [
                FFMPEG_BIN, "-y", "-i", raw_audio_path,
                "-ar", "24000", "-ac", "1", "-t", "12",
                target_wav_path
            ]
            subprocess.run(fallback_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _transcribe_reference(self, audio_path: str) -> str:
        pipe = self._load_asr_sync()
        try:
            res = pipe(audio_path)
            text = res.get("text", "").strip()
            return text
        except Exception as e:
            logger.warning(f"Whisper transcription failed: {e}")
            return ""

    async def create_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        remove_background_noise: bool = False,
    ) -> dict[str, Any]:
        """
        Registers reference audio for local zero-shot voice cloning.
        Cleans and normalizes audio, extracts exact verbatim ASR transcript,
        and saves profile for high-accuracy flow-matching conditioning.
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Reference audio not found: {audio_file_path}")

        voice_uuid = str(uuid.uuid4())
        provider_voice_id = f"self_hosted_{voice_uuid}"
        voice_dir = self.storage_dir / provider_voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)

        target_ref_wav = voice_dir / "reference.wav"

        # 1. Prepare pristine reference audio: 24kHz mono, trimmed silences, prime 12s chunk
        await asyncio.to_thread(self._prepare_reference_audio, audio_file_path, str(target_ref_wav))

        # 2. Extract or use exact reference transcript
        # Priority: explicit transcript provided by user, otherwise auto-transcribe with Whisper
        ref_text = ""
        if description and not description.startswith("Cloned for VoiceRep user") and len(description.strip()) > 3:
            ref_text = description.strip()

        if not ref_text:
            logger.info(f"Extracting verbatim ASR transcript for {provider_voice_id}...")
            transcribed = await asyncio.to_thread(self._transcribe_reference, str(target_ref_wav))
            if transcribed and len(transcribed) > 2:
                ref_text = transcribed
                logger.info(f"ASR extracted exact transcript: '{ref_text}'")

        if not ref_text:
            ref_text = "I hereby authorize VoiceRep to clone my voice for authorized speech synthesis."

        # Save reference text
        with open(voice_dir / "reference.txt", "w", encoding="utf-8") as f:
            f.write(ref_text)

        # Save metadata
        metadata = {
            "provider_voice_id": provider_voice_id,
            "name": name,
            "description": description or "",
            "ref_text": ref_text,
            "remove_background_noise": remove_background_noise,
        }
        with open(voice_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "voice_id": provider_voice_id,
            "requires_verification": False,
        }

    async def get_voice(self, provider_voice_id: str) -> dict[str, Any]:
        voice_dir = self.storage_dir / provider_voice_id
        meta_file = voice_dir / "metadata.json"
        if not meta_file.exists():
            raise KeyError(f"Voice profile {provider_voice_id} not found locally.")

        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def delete_voice(self, provider_voice_id: str) -> bool:
        voice_dir = self.storage_dir / provider_voice_id
        if voice_dir.exists():
            shutil.rmtree(voice_dir)
            logger.info(f"Deleted local voice profile {provider_voice_id}")
            return True
        return True

    def _synthesize_sync(
        self,
        voice_id: str,
        text: str,
        settings_dict: dict[str, Any],
        model_id: str,
    ) -> bytes:
        engine = self._load_engine_sync()
        voice_dir = self.storage_dir / voice_id
        ref_wav = voice_dir / "reference.wav"
        ref_txt_file = voice_dir / "reference.txt"

        if not ref_wav.exists():
            raise FileNotFoundError(f"Local voice reference audio not found for {voice_id}")

        ref_text = ""
        if ref_txt_file.exists():
            with open(ref_txt_file, "r", encoding="utf-8") as f:
                ref_text = f.read().strip()

        if not ref_text:
            ref_text = "I hereby authorize VoiceRep to clone my voice for authorized speech synthesis."

        # 1. Normalize input text
        norm_text = normalize_speech_text(text)
        if not norm_text:
            raise ValueError("Input text cannot be empty after normalization.")

        # 2. Derive tuned hyperparameters for optimal accuracy
        speed = float(settings_dict.get("speed", 1.0))
        similarity = float(settings_dict.get("similarity_boost", 0.8))
        # Map similarity boost (0.0 - 1.0) to classifier-free guidance (1.8 - 2.6)
        cfg_strength = 1.8 + (similarity * 0.8)
        if "fast" in (model_id or "").lower():
            nfe_steps = 16
        else:
            nfe_steps = max(int(settings.SELF_HOSTED_NFE_STEPS), 32)

        # 3. Phonetic chunking for long sequences (> 180 chars)
        chunks = chunk_text_by_sentence(norm_text, max_chars=180)
        logger.info(
            f"Synthesizing '{norm_text[:40]}...' ({len(chunks)} chunk(s)) with voice {voice_id} "
            f"(speed={speed}, CFG={cfg_strength:.2f}, steps={nfe_steps})..."
        )

        out_wav_path = voice_dir / f"temp_gen_{uuid.uuid4().hex}.wav"
        out_mp3_path = voice_dir / f"temp_gen_{uuid.uuid4().hex}.mp3"
        temp_chunk_paths: list[Path] = []

        try:
            if len(chunks) <= 1:
                chunk_text = chunks[0] if chunks else norm_text
                safe_seed = random.randint(1, 2147483647)
                res = engine.infer(
                    ref_file=str(ref_wav),
                    ref_text=ref_text,
                    gen_text=chunk_text,
                    speed=speed,
                    cfg_strength=cfg_strength,
                    sway_sampling_coef=-1.0,
                    nfe_step=nfe_steps,
                    remove_silence=True,
                    seed=safe_seed,
                    file_wave=str(out_wav_path),
                )
                if (not out_wav_path.exists() or out_wav_path.stat().st_size == 0) and res and res[0] is not None:
                    wav_arr = res[0]
                    if hasattr(wav_arr, "detach"):
                        wav_arr = wav_arr.detach().cpu().numpy()
                    if wav_arr.ndim > 1:
                        wav_arr = wav_arr.squeeze()
                    sr = res[1] or 24000
                    sf.write(str(out_wav_path), wav_arr, sr)
            else:
                # Multi-chunk sequential inference with silence stitching
                audio_segments: list[np.ndarray] = []
                sample_rate = 24000

                for chunk_text in chunks:
                    chunk_path = voice_dir / f"temp_chunk_{uuid.uuid4().hex}.wav"
                    temp_chunk_paths.append(chunk_path)
                    safe_seed = random.randint(1, 2147483647)
                    res = engine.infer(
                        ref_file=str(ref_wav),
                        ref_text=ref_text,
                        gen_text=chunk_text,
                        speed=speed,
                        cfg_strength=cfg_strength,
                        sway_sampling_coef=-1.0,
                        nfe_step=nfe_steps,
                        remove_silence=True,
                        seed=safe_seed,
                        file_wave=str(chunk_path),
                    )

                    seg = None
                    if res and res[0] is not None:
                        seg = res[0]
                        if hasattr(seg, "detach"):
                            seg = seg.detach().cpu().numpy()
                        if seg.ndim > 1:
                            seg = seg.squeeze()
                        if len(res) > 1 and res[1]:
                            sample_rate = res[1]
                    elif chunk_path.exists() and chunk_path.stat().st_size > 0:
                        seg, sample_rate = sf.read(str(chunk_path))
                        if seg.ndim > 1:
                            seg = seg[:, 0]

                    if seg is not None and len(seg) > 0:
                        audio_segments.append(seg.astype(np.float32))

                if not audio_segments:
                    raise RuntimeError("Audio synthesis produced no valid audio segments.")

                # Create 150ms natural silence padding between sentences
                silence_padding = np.zeros(int(sample_rate * 0.15), dtype=np.float32)
                stitched_audio = []
                for idx, segment in enumerate(audio_segments):
                    stitched_audio.append(segment)
                    if idx < len(audio_segments) - 1:
                        stitched_audio.append(silence_padding)

                final_wav = np.concatenate(stitched_audio)
                sf.write(str(out_wav_path), final_wav, sample_rate)

            # Convert generated 24kHz WAV to high-fidelity MP3 (256kbps)
            try:
                subprocess.run(
                    [
                        FFMPEG_BIN,
                        "-y",
                        "-i", str(out_wav_path),
                        "-c:a", "libmp3lame",
                        "-b:a", "256k",
                        "-ar", "24000",
                        str(out_mp3_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                with open(out_mp3_path, "rb") as f:
                    audio_bytes = f.read()
            except Exception as e:
                logger.warning(f"FFmpeg MP3 conversion fallback to WAV: {e}")
                with open(out_wav_path, "rb") as f:
                    audio_bytes = f.read()

            return audio_bytes

        finally:
            if out_wav_path.exists():
                out_wav_path.unlink(missing_ok=True)
            if out_mp3_path.exists():
                out_mp3_path.unlink(missing_ok=True)
            for cp in temp_chunk_paths:
                if cp.exists():
                    cp.unlink(missing_ok=True)

    async def synthesize(
        self,
        voice_id: str,
        text: str,
        settings: dict[str, Any],
        model_id: str = "f5_tts",
    ) -> bytes:
        async with self.infer_semaphore:
            return await asyncio.to_thread(
                self._synthesize_sync,
                voice_id,
                text,
                settings,
                model_id,
            )

    async def create_agent_session(
        self,
        provider_voice_id: str,
        agent_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate WebSocket connection URL for local conversational voice agent streaming.
        """
        session_id = str(uuid.uuid4())
        ws_base = settings.BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://")
        signed_url = f"{ws_base}/api/v1/agents/ws/{session_id}"

        session_config = {
            "agent_id": f"self_hosted_agent_{session_id}",
            "overrides": {
                "tts": {
                    "voice_id": provider_voice_id,
                },
                "agent": {
                    "prompt": {
                        "prompt": agent_config.get("system_prompt", ""),
                    },
                    "first_message": agent_config.get("first_message", ""),
                    "language": agent_config.get("language", "en"),
                },
            },
        }

        return {
            "signed_url": signed_url,
            "agent_id": f"self_hosted_agent_{session_id}",
            "session_config": session_config,
        }


self_hosted_provider = SelfHostedProvider()
