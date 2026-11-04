import logging
import os
from typing import Any, Optional
import httpx
from app.core.config import settings
from app.providers.base import VoiceProvider

logger = logging.getLogger("voicerep.elevenlabs")

BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsProvider(VoiceProvider):
    @property
    def api_key(self) -> Optional[str]:
        return settings.ELEVENLABS_API_KEY or os.environ.get("ELEVENLABS_API_KEY")

    @property
    def agent_id(self) -> Optional[str]:
        return settings.ELEVENLABS_AGENT_ID or os.environ.get("ELEVENLABS_AGENT_ID")

    def _get_headers(self) -> dict[str, str]:
        key = self.api_key
        if not key:
            raise ValueError(
                "ElevenLabs API key is not configured. Please set ELEVENLABS_API_KEY in your .env file."
            )
        return {
            "xi-api-key": key,
        }

    async def create_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        remove_background_noise: bool = False,
    ) -> dict[str, Any]:
        headers = self._get_headers()
        url = f"{BASE_URL}/voices/add"

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        filename = os.path.basename(audio_file_path)

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_file_path, "rb") as f:
                files = {
                    "files": (filename, f, "audio/mpeg")
                }
                data: dict[str, Any] = {
                    "name": name,
                    "remove_background_noise": str(remove_background_noise).lower(),
                }
                if description:
                    data["description"] = description

                response = await client.post(url, headers=headers, data=data, files=files)

        if response.status_code == 200:
            res_data = response.json()
            return {
                "voice_id": res_data.get("voice_id"),
                "requires_verification": res_data.get("requires_verification", False),
            }
        else:
            error_text = response.text
            try:
                err_json = response.json()
                detail = err_json.get("detail", {})
                if isinstance(detail, dict):
                    status_flag = detail.get("status", "")
                    msg = detail.get("message", "")
                    if status_flag == "can_not_use_instant_voice_cloning" or "subscription tier" in msg.lower():
                        error_text = "Instant Voice Cloning is not available on ElevenLabs' Free tier. ElevenLabs requires at least a Starter subscription ($5/mo) to create custom voice clones via the API."
                    else:
                        error_text = msg or status_flag or error_text
                elif isinstance(detail, str):
                    error_text = detail
            except Exception:
                pass

            logger.error(f"ElevenLabs voice clone failed ({response.status_code}): {error_text}")
            raise RuntimeError(f"Voice cloning provider error ({response.status_code}): {error_text}")

    async def get_voice(self, provider_voice_id: str) -> dict[str, Any]:
        headers = self._get_headers()
        url = f"{BASE_URL}/voices/{provider_voice_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise KeyError(f"Voice {provider_voice_id} not found on provider.")
        else:
            raise RuntimeError(f"Failed to fetch voice details ({response.status_code}): {response.text}")

    async def delete_voice(self, provider_voice_id: str) -> bool:
        headers = self._get_headers()
        url = f"{BASE_URL}/voices/{provider_voice_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(url, headers=headers)

        if response.status_code in (200, 204):
            return True
        elif response.status_code == 404:
            # Voice already deleted or nonexistent on provider
            return True
        else:
            logger.error(f"Failed to delete provider voice ({response.status_code}): {response.text}")
            return False

    async def synthesize(
        self,
        voice_id: str,
        text: str,
        settings: dict[str, Any],
        model_id: str = "eleven_multilingual_v2",
    ) -> bytes:
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "audio/mpeg"

        url = f"{BASE_URL}/text-to-speech/{voice_id}/stream"

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": settings.get("stability", 0.5),
                "similarity_boost": settings.get("similarity_boost", 0.75),
                "speed": settings.get("speed", 1.0),
                "style": settings.get("style", 0.0),
            },
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.content
        else:
            error_text = response.text
            try:
                err_json = response.json()
                detail = err_json.get("detail", {})
                if isinstance(detail, dict):
                    status_flag = detail.get("status", "")
                    msg = detail.get("message", "")
                    if status_flag == "can_not_use_instant_voice_cloning" or "subscription tier" in msg.lower():
                        error_text = "Instant Voice Cloning is not available on ElevenLabs' Free tier. ElevenLabs requires at least a Starter subscription ($5/mo) to create custom voice clones via the API."
                    else:
                        error_text = msg or status_flag or error_text
                elif isinstance(detail, str):
                    error_text = detail
            except Exception:
                pass

            logger.error(f"TTS generation failed ({response.status_code}): {error_text}")
            raise RuntimeError(f"TTS provider error ({response.status_code}): {error_text}")

    async def create_agent_session(
        self,
        provider_voice_id: str,
        agent_config: dict[str, Any],
    ) -> dict[str, Any]:
        agent_id = self.agent_id or agent_config.get("agent_id")
        if not agent_id:
            raise ValueError(
                "ElevenLabs Conversational AI Agent ID is not configured. Please set ELEVENLABS_AGENT_ID."
            )

        headers = self._get_headers()
        url = f"{BASE_URL}/convai/conversation/get-signed-url?agent_id={agent_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            error_text = response.text
            try:
                err_json = response.json()
                detail = err_json.get("detail", {})
                if isinstance(detail, dict):
                    status_flag = detail.get("status", "")
                    msg = detail.get("message", "")
                    if status_flag == "can_not_use_instant_voice_cloning" or "subscription tier" in msg.lower():
                        error_text = "Instant Voice Cloning is not available on ElevenLabs' Free tier. ElevenLabs requires at least a Starter subscription ($5/mo) to create custom voice clones via the API."
                    else:
                        error_text = msg or status_flag or error_text
                elif isinstance(detail, str):
                    error_text = detail
            except Exception:
                pass
            raise RuntimeError(f"Failed to get ConvAI signed URL ({response.status_code}): {error_text}")

        data = response.json()
        signed_url = data.get("signed_url")

        # Session configuration overrides
        session_config = {
            "agent_id": agent_id,
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
            "agent_id": agent_id,
            "session_config": session_config,
        }


elevenlabs_provider = ElevenLabsProvider()
