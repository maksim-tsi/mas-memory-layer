import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.getcwd())

from src.llm.client import LLMClient


def test_factory_with_env_vars():
    print("Testing LLMClient.from_env() with mock environment variables...")

    with (
        patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "fake_google_key",
                "GROQ_API_KEY": "fake_groq_key",
                "MISTRAL_API_KEY": "fake_mistral_key",
                "PHOENIX_COLLECTOR_ENDPOINT": "",  # Disable phoenix for this test
            },
        ),
        patch.dict(
            sys.modules,
            {
                "google.genai": MagicMock(),
                "groq": MagicMock(),
                "mistralai": MagicMock(),
                "src.llm.providers.gemini": MagicMock(),
                "src.llm.providers.groq": MagicMock(),
                "src.llm.providers.mistral": MagicMock(),
            },
        ),
    ):
        # We need to mock the provider classes specifically so register_provider works
        # But wait, from_env imports them.
        # Let's rely on the real imports but mock `__init__` or just let them fail if they try to connect?
        # Actually, `GeminiProvider` etc. import packages.

        # Use a simpler approach: Just check if register_provider is called correctly?
        # No, I want to verify the logic in from_env.

        # Let's try to run it. If it fails due to missing dependencies, I'll mock.
        # The environment likely has the dependencies installed as per previous turns.
        pass

    # Real test
    # We will set env vars and check the client's registered providers.
    # Note: Real providers might try to validate keys or connect.
    # GeminiProvider init: `self.client = genai.Client(api_key=api_key)` -> might be safe if lazy.
    # GroqProvider init: `self.client = Groq(...)` -> usually safe.
    # MistralProvider init: `self.client = Mistral(...)` -> usually safe.

    os.environ["GOOGLE_API_KEY"] = "fake_google_key"
    os.environ["GROQ_API_KEY"] = "fake_groq_key"
    os.environ["MISTRAL_API_KEY"] = "fake_mistral_key"
    # Ensure phoenix doesn't complain
    if "PHOENIX_COLLECTOR_ENDPOINT" in os.environ:
        del os.environ["PHOENIX_COLLECTOR_ENDPOINT"]

    try:
        client = LLMClient.from_env()
        providers = client.available_providers()
        print(f"Registered providers: {providers}")

        expected = {"gemini", "groq", "mistral"}
        if set(providers) == expected:
            print("SUCCESS: All providers registered.")
        else:
            print(f"FAILURE: Expected {expected}, got {set(providers)}")
            sys.exit(1)

        # Check priorities
        # We can't easily check priorities without accessing private _configs,
        # but we can check if generate calls them in order?
        # That would require mocking the generate methods.

    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_factory_with_env_vars()
