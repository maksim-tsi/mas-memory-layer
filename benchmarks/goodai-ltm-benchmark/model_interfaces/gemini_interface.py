import os
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path

from google import genai
from google.genai import types

from model_interfaces.interface import ChatSession


@dataclass
class GeminiProInterface(ChatSession):
    is_local: bool = True  # TODO: Capture cost information
    _client: genai.Client = field(init=False)
    _chat_history: list[types.Content] = field(default_factory=list)
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))

    @property
    def history_path(self) -> Path:
        return self.save_path.joinpath("history.dat")

    def __post_init__(self) -> None:
        super().__post_init__()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self._client = genai.Client(api_key=api_key)
        self.reset()

    def reply(self, user_message: str, agent_response: str | None = None) -> str:
        # Add user message to local history
        self._chat_history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        if agent_response is None:
            agent_response = self._generate_with_retry(self._chat_history)

        # Add model response to local history
        self._chat_history.append(
            types.Content(role="model", parts=[types.Part.from_text(text=agent_response)])
        )

        time.sleep(0.1)
        return agent_response

    def _generate_with_retry(self, history: list[types.Content]) -> str:
        # Configuration for the generation
        config = types.GenerateContentConfig(
            temperature=0.0,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
                ),
            ],
            automatic_function_calling={"disable": True},
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=history,
                    config=config,
                )

                if not response.text:
                    print(
                        f"Reason: Empty response or blocked. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                    )
                    raise ValueError("Empty response from model")

                return str(response.text)

            except Exception as e:
                print(f"Generation error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 10 seconds.")
                    time.sleep(10)
                else:
                    raise

        raise RuntimeError("Failed to generate content after retries")

    def reset(self, history: list[types.Content] | None = None) -> None:
        self._chat_history = history or []

    def save(self) -> None:
        # We pickling the list of Content objects
        # Note: newer SDK objects might not be pickle-friendly across versions,
        # but for a self-contained run it should be fine.
        with open(self.history_path, "wb") as fd:
            pickle.dump(self._chat_history, fd)

    def load(self) -> None:
        if self.history_path.exists():
            with open(self.history_path, "rb") as fd:
                self.reset(pickle.load(fd))

    def token_len(self, text: str) -> int:
        # Use the SDK's count_tokens method
        response = self._client.models.count_tokens(
            model=self.model,
            contents=[types.Content(parts=[types.Part.from_text(text=text)])],
        )
        time.sleep(0.1)
        return response.total_tokens or 0
