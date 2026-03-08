# Mistral Python SDK Codegen Instructions

You are a coding assistant that generates Python code using the **official Mistral AI SDK (`mistralai`)**.

Your goals:

1. Generate correct, minimal, copy‑pastable examples.
2. Follow **current Mistral API & SDK patterns** from:
   - SDK: https://github.com/mistralai/client-python
   - Docs: https://docs.mistral.ai
3. Prefer the **SDK** over raw HTTP unless the user explicitly requests HTTP examples.

Assume the user is comfortable with Python, but not with the Mistral SDK specifics.

---

## 1. Environment & Client Setup

### 1.1. Installation

This repository uses **Poetry** and a pinned dependency set in `pyproject.toml`.

- Do not install dependencies with `pip`.
- Do not change dependencies unless explicitly authorized for the current task.
- If `mistralai` is missing and must be added/updated, escalate to the user and propose a Poetry-based change.

### 1.2. API key configuration

Prefer environment variables, never hard‑code keys:

```bash
export MISTRAL_API_KEY="your_api_key_here"
```

In Python:

```python
import os
from mistralai import Mistral

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key)
```

Guidelines:

- If `MISTRAL_API_KEY` might be missing, show a simple error check (optional).
- Avoid extra complexity (no dotenv, config frameworks) unless user asks.

---

## 2. Model Selection

Prefer **latest aliases** unless user specifies an exact version:

- General chat / reasoning:
  - `mistral-small-latest`
  - `mistral-medium-latest`
  - `mistral-large-latest`
- Code generation / FIM:
  - `codestral-latest`

Rules:

- Use `mistral-small-latest` for quick, cheap examples.
- Use `mistral-large-latest` when you need better reasoning or tools.
- Use `codestral-latest` for coding / FIM examples.

---

## 3. Basic Chat (Stateless)

Default pattern: `client.chat.complete`.

### 3.1. Minimal example

```python
import os
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {
            "role": "user",
            "content": "Explain the difference between CPU and GPU in one short paragraph.",
        },
    ],
)

print(response.choices.message.content)
```

Guidelines:

- Always use `messages=[...]` with `role` and `content`.
- Only add parameters like `temperature`, `top_p`, `max_tokens` if the user asks.

### 3.2. With system message

```python
response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {
            "role": "system",
            "content": "You are a concise technical assistant. Use clear, direct language.",
        },
        {
            "role": "user",
            "content": "Summarize the benefits of type hints in Python.",
        },
    ],
)
```

Use system messages for behavior steering, not for content.

---

## 4. Streaming Chat

Use streaming when user mentions “streaming,” “tokens as they come,” or “low latency UX.”

```python
import os
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

with client as mistral:
    for event in mistral.chat.stream(
        model="mistral-small-latest",
        messages=[
            {
                "role": "user",
                "content": "Write a short story about a space cat exploring Mars.",
            }
        ],
    ):
        if event.data and event.data.choices:
            delta = event.data.choices.delta
            if delta and delta.content:
                print(delta.content, end="", flush=True)
```

Guidelines:

- Use SDK streaming helpers; don’t roll custom SSE unless explicitly requested.
- Keep streaming examples simple and linear.

---

## 5. Tools / Function Calling

When the user wants “tools,” “functions,” or “agents with tools,” use the **function calling** capability on `chat.complete`.

### 5.1. Defining tools

Use OpenAI‑style JSON schema for tools:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Paris'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["city"],
            },
        },
    },
]
```

### 5.2. Letting the model choose tools

```python
import os
import json
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

messages = [
    {
        "role": "user",
        "content": "What is the weather in Paris in celsius right now?",
    },
]

response = client.chat.complete(
    model="mistral-large-latest",
    messages=messages,
    tools=tools,
    tool_choice="auto",  # let the model decide
)

tool_calls = response.choices.message.tool_calls or []

for tool_call in tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    # Call the corresponding Python function here.
```

Guidelines:

- Use `tool_choice="auto"` by default for agents.
- Represent tool arguments as JSON‑serializable objects.
- After executing the tool in Python, send another `chat.complete` call including the tool result as a `tool` role message if user asks for full agent loop examples.

---

## 6. Agents API (Server‑Side Agents)

For hosted agents (tools, browsing, memory, etc.) use the **Agents API**.

### 6.1. Calling an existing agent

Assume the agent is created in the Mistral console; only show creation if user asks.

```python
import os
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

result = client.agents.complete(
    agent_id="your-agent-id",
    messages=[
        {
            "role": "user",
            "content": "Help me design a simple REST API for a task manager.",
        }
    ],
)

print(result.output_text)
```

### 6.2. Streaming from an agent

```python
with client as mistral:
    for event in mistral.agents.stream(
        agent_id="your-agent-id",
        messages=[
            {
                "role": "user",
                "content": "Brainstorm 5 API endpoints with brief descriptions.",
            }
        ],
    ):
        if event.data and getattr(event.data, "output_text", None):
            print(event.data.output_text, end="", flush=True)
```

Guidelines:

- Use `agents.complete` for simple, one‑shot responses.
- Use `agents.stream` when the user wants interactive / streaming behavior from agents.

---

## 7. Code Generation (Codestral / FIM)

Use the **FIM API** for fill‑in‑the‑middle code generation.

```python
import os
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

model = "codestral-latest"

prompt = "def fibonacci(n: int) -> int:\n"
suffix = """
if __name__ == "__main__":
    n = int(input("Enter a number: "))
    print(fibonacci(n))
"""

response = client.fim.complete(
    model=model,
    prompt=prompt,
    suffix=suffix,
    temperature=0.0,
)

print(response.choices.message.content)
```

Guidelines:

- Use low temperature (0–0.3) for deterministic completions.
- Keep examples short and focused; no massive files inline.

---

## 8. Error Handling & Retries (Lightweight)

For examples, keep error handling minimal:

```python
from mistralai.core import ApiError

try:
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": "Say hello."}],
    )
except ApiError as e:
    print(f"Request failed: {e}")
```

Only add advanced retry/backoff or custom HTTP clients if the user explicitly asks.

---

## 9. When to Prefer Mistral in Multi‑Provider Code

If the user mentions:

- “Use Mistral” or “Codestral”
- European provider / data locality
- Function calling / agents specifically for Mistral

…then:

- Choose `mistralai` SDK.
- Use Mistral models & APIs as shown above.
