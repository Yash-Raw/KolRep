from abc import ABC, abstractmethod
from typing import Any, Optional


class VoiceProvider(ABC):
    @abstractmethod
    async def create_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        remove_background_noise: bool = False,
        transcript: Optional[str] = None,
    ) -> dict[str, Any]:
        """Clone an authorized voice using instant voice cloning."""
        pass

    @abstractmethod
    async def get_voice(self, provider_voice_id: str) -> dict[str, Any]:
        """Retrieve voice details from the provider."""
        pass

    @abstractmethod
    async def delete_voice(self, provider_voice_id: str) -> bool:
        """Delete cloned voice from the provider."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        voice_id: str,
        text: str,
        settings: dict[str, Any],
        model_id: str = "F5TTS_v1_Base",
    ) -> bytes:
        """Synthesize text into speech audio bytes."""
        pass
