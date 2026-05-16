from __future__ import annotations

from app.core.config import Settings

from .base import ExtractionProvider


def build_provider(settings: Settings) -> ExtractionProvider:
    match settings.EXTRACTION_PROVIDER:
        case "fixture":
            from .fixture import FixtureProvider
            return FixtureProvider(seeds_dir=settings.FIXTURE_SEEDS_DIR)
        case "claude":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY must be set when EXTRACTION_PROVIDER=claude")
            from .claude import ClaudeProvider
            return ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.CLAUDE_MODEL)
        case "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY must be set when EXTRACTION_PROVIDER=gemini")
            from .gemini import GeminiProvider
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        case _:
            raise ValueError(f"Unknown EXTRACTION_PROVIDER: {settings.EXTRACTION_PROVIDER!r}")
