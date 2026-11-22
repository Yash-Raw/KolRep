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

# Ensure torchaudio safely falls back to soundfile if torchcodec is unavailable
try:
    import torchaudio
    _orig_ta_load = torchaudio.load
    def _safe_ta_load(filepath, *args, **kwargs):
        try:
            return _orig_ta_load(filepath, *args, **kwargs)
        except Exception:
            data, sr = sf.read(str(filepath), dtype="float32")
            tensor = torch.from_numpy(data)
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0)
            else:
                tensor = tensor.t()
            return tensor, sr

    _orig_ta_save = torchaudio.save
    def _safe_ta_save(filepath, src, sample_rate, *args, **kwargs):
        try:
            return _orig_ta_save(filepath, src, sample_rate, *args, **kwargs)
        except Exception:
            data = src.detach().cpu().numpy()
            if data.ndim == 2:
                data = data.T
            sf.write(str(filepath), data, sample_rate)

    torchaudio.load = _safe_ta_load
    torchaudio.save = _safe_ta_save
    if hasattr(torchaudio, "load_with_torchcodec"):
        torchaudio.load_with_torchcodec = _safe_ta_load
    if hasattr(torchaudio, "save_with_torchcodec"):
        torchaudio.save_with_torchcodec = _safe_ta_save

    try:
        import torchaudio._torchcodec
        torchaudio._torchcodec.load_with_torchcodec = _safe_ta_load
        torchaudio._torchcodec.save_with_torchcodec = _safe_ta_save
    except Exception:
        pass
except Exception:
    pass

from app.core.config import settings
from app.providers.base import VoiceProvider
from app.services.audio_service import FFMPEG_BIN

logger = logging.getLogger("kolrep.self_hosted")

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

    def _load_engine_sync(self, force_cpu: bool = False) -> Any:
        if self._engine is not None and not force_cpu:
            return self._engine
        
        logger.info("Initializing Self-Hosted F5-TTS Engine...")
        from f5_tts.api import F5TTS

        device = "cpu" if force_cpu else self._get_device()
        logger.info(f"Loading F5TTS ({settings.SELF_HOSTED_MODEL}) on device: {device}")
        
        hf_cache = os.environ.get("HF_HOME") or (
            str(Path(settings.DESKTOP_DATA_DIR) / "models") if settings.DESKTOP_DATA_DIR else None
        )

        try:
            engine = F5TTS(
                model=settings.SELF_HOSTED_MODEL,
                device=device,
                hf_cache_dir=hf_cache,
            )
        except Exception as e:
            if device != "cpu":
                logger.warning(f"Failed to load F5TTS on {device} ({e}). Falling back to CPU...")
                device = "cpu"
                engine = F5TTS(
                    model=settings.SELF_HOSTED_MODEL,
                    device=device,
                    hf_cache_dir=hf_cache,
                )
            else:
                raise
        self._engine = engine
        logger.info(f"Self-Hosted F5-TTS Engine initialized successfully on {device}.")
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
        import sys
        sys.modules["torchcodec"] = None
        sys.modules["torchcodec.decoders"] = None
        try:
            import transformers.utils.import_utils as _hf_iu
            _hf_iu.is_torchcodec_available = lambda: False
        except Exception:
            pass
        from transformers import pipeline
        logger.info("Loading Whisper ASR pipeline for reference audio transcription...")
        pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny",
            device="cpu",
        )
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
        Cleans leading/trailing dead silence with two-pass reversal, limits duration to prime 15s speech chunk,
        and resamples to 24000 Hz mono 16-bit PCM WAV (F5-TTS native frequency).
        """
        cmd = [
            FFMPEG_BIN,
            "-y",
            "-i", raw_audio_path,
            "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB:detection=peak,areverse,silenceremove=start_periods=1:start_duration=0.2:start_threshold=-45dB:detection=peak,areverse,aformat=sample_fmts=s16:sample_rates=24000:channel_layouts=mono",
            "-t", "15",
            target_wav_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.warning(f"Audio cleaning filter warning, falling back to direct wav convert: {res.stderr.decode()}")
            fallback_cmd = [
                FFMPEG_BIN, "-y", "-i", raw_audio_path,
                "-ar", "24000", "-ac", "1", "-t", "15",
                target_wav_path
            ]
            subprocess.run(fallback_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _transcribe_reference(self, audio_path: str) -> str:
        try:
            import librosa
            data, sr = sf.read(str(audio_path), dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != 16000:
                data = librosa.resample(data, orig_sr=sr, target_sr=16000)

            pipe = self._load_asr_sync()
            res = pipe(
                {"raw": data, "sampling_rate": 16000},
                generate_kwargs={"language": "en", "task": "transcribe"},
            )
            text = res.get("text", "").strip()
            return text
        except Exception as e:
            import traceback
            logger.warning(f"Whisper transcription failed or unavailable: {e}\n{traceback.format_exc()}")
            return ""

    def _get_or_repair_reference_text(self, voice_id: str, voice_dir: Path) -> str:
        """
        Reads reference text and automatically detects/repairs corrupted voice profiles
        that contain boilerplate authorization text instead of verbatim speech.
        """
        ref_txt_file = voice_dir / "reference.txt"
        ref_wav = voice_dir / "reference.wav"
        ref_text = ""

        if ref_txt_file.exists():
            try:
                with open(ref_txt_file, "r", encoding="utf-8") as f:
                    ref_text = f.read().strip()
            except Exception:
                ref_text = ""

        # Detect boilerplate authorization strings
        is_corrupt = False
        lower_ref = ref_text.lower()
        if not ref_text or any(phrase in lower_ref for phrase in [
            "authorize kolrep",
            "hereby authorize",
            "personalized speech synthesis",
            "authorized speech synthesis",
        ]):
            is_corrupt = True

        if is_corrupt and ref_wav.exists():
            logger.info(f"Self-healing voice profile {voice_id}: re-transcribing reference audio with Whisper ASR...")
            transcribed = self._transcribe_reference(str(ref_wav))
            if transcribed and len(transcribed.strip()) > 2:
                ref_text = transcribed.strip()
                logger.info(f"Voice profile {voice_id} successfully restored to verbatim transcript: '{ref_text[:60]}...'")
                try:
                    with open(ref_txt_file, "w", encoding="utf-8") as f:
                        f.write(ref_text)
                    meta_file = voice_dir / "metadata.json"
                    if meta_file.exists():
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            meta = json.load(mf)
                        meta["ref_text"] = ref_text
                        with open(meta_file, "w", encoding="utf-8") as mf:
                            json.dump(meta, mf, indent=2)
                except Exception as save_err:
                    logger.warning(f"Failed to persist repaired reference text for {voice_id}: {save_err}")

        if not ref_text:
            ref_text = "I hereby authorize KolRep to clone my voice for authorized speech synthesis."

        return ref_text

    async def create_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        remove_background_noise: bool = False,
        transcript: Optional[str] = None,
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

        # 1. Prepare pristine reference audio: 24kHz mono, trimmed leading/trailing silences, prime chunk
        await asyncio.to_thread(self._prepare_reference_audio, audio_file_path, str(target_ref_wav))

        # 2. Extract or use exact reference transcript (never use description as spoken text)
        candidate_text = (transcript or "").strip()

        # Reject boilerplate authorization strings from polluting conditioning text
        is_boilerplate = False
        lower_cand = candidate_text.lower()
        if any(phrase in lower_cand for phrase in [
            "authorize kolrep",
            "hereby authorize",
            "personalized speech synthesis",
            "authorized speech synthesis",
        ]):
            is_boilerplate = True

        ref_text = ""
        # Primary: Run Whisper ASR on target_ref_wav to capture verbatim ground truth
        logger.info(f"Extracting verbatim ASR transcript for {provider_voice_id}...")
        transcribed = await asyncio.to_thread(self._transcribe_reference, str(target_ref_wav))
        if transcribed and len(transcribed.strip()) > 2:
            logger.info(f"ASR extracted exact transcript: '{transcribed}'")
            if candidate_text and not is_boilerplate:
                ref_text = candidate_text
            else:
                ref_text = transcribed.strip()
        elif candidate_text and not is_boilerplate:
            ref_text = candidate_text

        if not ref_text:
            ref_text = "I hereby authorize KolRep to clone my voice for authorized speech synthesis."

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

        # Ensure reference text is healed if corrupted
        ref_text = await asyncio.to_thread(self._get_or_repair_reference_text, provider_voice_id, voice_dir)

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
            meta["ref_text"] = ref_text
            return meta

    async def delete_voice(self, provider_voice_id: str) -> bool:
        voice_dir = self.storage_dir / provider_voice_id
        if voice_dir.exists():
            shutil.rmtree(voice_dir)
            logger.info(f"Deleted local voice profile {provider_voice_id}")
            return True
        return True

    def _synthesize_sync_inner(
        self,
        voice_id: str,
        text: str,
        settings_dict: dict[str, Any],
        model_id: str,
    ) -> bytes:
        engine = self._load_engine_sync()
        voice_dir = self.storage_dir / voice_id
        ref_wav = voice_dir / "reference.wav"

        if not ref_wav.exists():
            raise FileNotFoundError(f"Local voice reference audio not found for {voice_id}")

        # Retrieve or automatically heal reference text
        ref_text = self._get_or_repair_reference_text(voice_id, voice_dir)

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
            nfe_steps = 24
        else:
            nfe_steps = max(int(settings.SELF_HOSTED_NFE_STEPS), 36)

        safe_seed = random.randint(1, 2147483647)
        logger.info(
            f"Synthesizing '{norm_text[:40]}...' with voice {voice_id} "
            f"(speed={speed}, CFG={cfg_strength:.2f}, steps={nfe_steps}, seed={safe_seed})..."
        )

        out_wav_path = voice_dir / f"temp_gen_{uuid.uuid4().hex}.wav"

        try:
            # Use F5-TTS native infer which manages chunking, batching, and cross-fading seamlessly
            res = engine.infer(
                ref_file=str(ref_wav),
                ref_text=ref_text,
                gen_text=norm_text,
                speed=speed,
                cfg_strength=cfg_strength,
                sway_sampling_coef=-1.0,
                nfe_step=nfe_steps,
                cross_fade_duration=0.15,
                remove_silence=True,
                seed=safe_seed,
                file_wave=str(out_wav_path),
            )

            # Ensure valid WAV exists
            if (not out_wav_path.exists() or out_wav_path.stat().st_size == 0) and res and res[0] is not None:
                wav_arr = res[0]
                if hasattr(wav_arr, "detach"):
                    wav_arr = wav_arr.detach().cpu().numpy()
                if wav_arr.ndim > 1:
                    wav_arr = wav_arr.squeeze()
                sr = res[1] or 24000
                sf.write(str(out_wav_path), wav_arr, sr)

            if not out_wav_path.exists() or out_wav_path.stat().st_size == 0:
                raise RuntimeError("Audio synthesis produced no valid audio output.")

            # Return pristine uncompressed 24kHz PCM WAV bytes
            with open(out_wav_path, "rb") as f:
                audio_bytes = f.read()

            return audio_bytes

        finally:
            if out_wav_path.exists():
                out_wav_path.unlink(missing_ok=True)

    def _synthesize_sync(
        self,
        voice_id: str,
        text: str,
        settings_dict: dict[str, Any],
        model_id: str,
    ) -> bytes:
        try:
            return self._synthesize_sync_inner(voice_id, text, settings_dict, model_id)
        except Exception as e:
            if self._get_device() == "mps" and not getattr(self, "_in_cpu_fallback", False):
                logger.warning(f"Inference on MPS failed ({e}). Automatically retrying with CPU fallback...")
                self._in_cpu_fallback = True
                try:
                    self._engine = self._load_engine_sync(force_cpu=True)
                    return self._synthesize_sync_inner(voice_id, text, settings_dict, model_id)
                finally:
                    self._in_cpu_fallback = False
            raise

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


self_hosted_provider = SelfHostedProvider()
