# Groq Python SDK Codegen Instructions

You are a coding assistant that generates Python code using the **official Groq Python SDK (`groq`)** and the OpenAI‑style Chat Completions API.

Your goals:

1. Generate correct, minimal, copy‑pastable examples.
2. Follow **current Groq API & SDK patterns** from:
   - SDK: https://github.com/groq/groq-python
   - Docs: https://console.groq.com/docs
3. Prefer the **SDK** over raw HTTP unless the user explicitly requests HTTP examples.

Assume the user is comfortable with Python, but not with the Groq SDK specifics.

---

## 1. Environment & Client Setup

### 1.1. Installation

This repository uses **Poetry** and a pinned dependency set in `pyproject.toml`.

- Do not install dependencies with `pip`.
- Do not change dependencies unless explicitly authorized for the current task.
- If `groq` is missing and must be added/updated, escalate to the user and propose a Poetry-based change.

### 1.2. API key configuration

Use environment variables, never hard‑code keys:

```bash
export GROQ_API_KEY="your_api_key_here"
```

In Python:

```python
import os
from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
```

Guidelines:

- Do not introduce dotenv or config frameworks unless requested.
- Ensure examples work with `python main.py` in a typical environment.

---

## 2. Model Selection

Groq exposes multiple Llama and Mixtral‑family models. Prefer recent Llama 3.x “versatile” models by default:

- General chat / reasoning:
  - `llama-3.3-70b-versatile` (or latest “70b versatile” model)
- Lower‑latency / cheaper:
  - `llama3-8b-8192` or the most recent “8b” model

Rules:

- Use `llama-3.3-70b-versatile` in main examples unless the user mentions latency/cost constraints.
- If the user asks “what models exist,” suggest listing via `client.models.list()` rather than hard‑coding a long list.

---

## 3. Basic Chat (Stateless)

Default pattern: `client.chat.completions.create`.

### 3.1. Minimal example

```python
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of low latency LLMs in one short paragraph.",
        }
    ],
)

print(chat_completion.choices.message.content)
```

Guidelines:

- Use the standard OpenAI Chat Completions `messages` format.
- Avoid unnecessary parameters in simple examples.

### 3.2. With system message

```python
chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "system",
            "content": "You are a concise, highly technical assistant.",
        },
        {
            "role": "user",
            "content": "Summarize the benefits of static typing in large Python codebases.",
        },
    ],
)
```

---

## 4. Streaming Chat

Use streaming when the user cares about “first token” latency or interactive output.

```python
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

with client.chat.completions.stream(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": "Write a short sci‑fi story about a debugging robot.",
        }
    ],
) as stream:
    for event in stream:
        delta = event.choices.delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
```

Guidelines:

- Use the SDK’s `stream` context manager.
- Keep examples simple (single user message).

---

## 5. Tools / Function Calling

Groq supports OpenAI‑style tools/function calling on chat completions. Use that when the user mentions “tools,” “function calling,” or “agents with tools.”

### 5.1. Defining tools

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the latest stock price for a ticker symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol, e.g. 'GOOG'",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]
```

### 5.2. Letting the model choose tools

```python
import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

messages = [
    {
        "role": "user",
        "content": "What is the current price of GOOG?",
    },
]

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)

choice = resp.choices
tool_calls = choice.message.tool_calls or []

for tool_call in tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    # Call your Python implementation for `name(**args)` here.
```

Guidelines:

- Use `tool_choice="auto"` by default.
- After executing the tool, send another `chat.completions.create` including the tool response as a `tool` role message if the user wants a full agent loop example.

---

## 6. JSON / Structured Outputs

When the user wants structured data, guide towards JSON output.

If the model supports it, you can use `response_format={"type": "json_object"}`; otherwise, rely on clear instructions plus `json.loads`.

Example (conceptual):

```python
import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": (
                "Summarize this text and return JSON with fields "
                "`title` (string) and `summary` (string): "
                "\"Groq provides low-latency inference for LLMs.\""
            ),
        }
    ],
    # Use this if/when supported for the specific model:
    # response_format={"type": "json_object"},
)

content = resp.choices.message.content
data = json.loads(content)
print(data["title"], data["summary"])
```

Guidelines:

- Make the JSON schema explicit in the prompt.
- Default to `json.loads` on `message.content` in examples.

---

## 7. Async Usage

If the user asks for async, use `AsyncGroq`:

```python
import os
import asyncio
from groq import AsyncGroq

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

async def main() -> None:
    chat_completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": "Explain event loops in Python in a few sentences.",
            }
        ],
    )
    print(chat_completion.choices.message.content)

asyncio.run(main())
```

Guidelines:

- Keep async examples as close as possible to the sync versions.
- Only introduce async when user cares about concurrency or non‑blocking IO.

---

## 8. Error Handling & Retries (Lightweight)

Keep error handling minimal in examples:

```python
from groq import Groq, APIStatusError
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

try:
    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello."}],
    )
except APIStatusError as e:
    print(f"Request failed: {e}")
```

Only show advanced retry/backoff logic if explicitly requested.

---

## 9. When to Prefer Groq in Multi‑Provider Code

If the user mentions:

- **Low latency**, **throughput**, or **real‑time UX**
- Running Llama / Mixtral models via an **OpenAI‑style** API
- “Use Groq” or a Groq‑specific model name

…then:

- Use the `groq` SDK and examples from this file.
- Emphasize that most OpenAI Chat Completions examples can be ported by:
  - Changing the import to `from groq import Groq`
  - Using `GROQ_API_KEY`
  - Updating the `model` string to a Groq model ID.
```
