from typing import Optional
from app.core.config import settings
from app.providers.base import VoiceProvider
from app.providers.self_hosted import SelfHostedProvider, self_hosted_provider


def get_voice_provider(provider_name: Optional[str] = None) -> VoiceProvider:
    """
    Returns the active 100% self-hosted VoiceProvider instance.
    """
    return self_hosted_provider


__all__ = [
    "VoiceProvider",
    "SelfHostedProvider",
    "self_hosted_provider",
    "get_voice_provider",
]
