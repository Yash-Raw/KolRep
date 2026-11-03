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
        model_id: str = "eleven_multilingual_v2",
    ) -> bytes:
        """Synthesize text into speech audio bytes."""
        pass

    @abstractmethod
    async def create_agent_session(
        self,
        provider_voice_id: str,
        agent_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a signed WebSocket URL and session parameters for a conversational AI session."""
        pass
