# 🚀 Quickstart Guide

This guide will walk you through setting up ICE for the first time. We focus on the **Zero-Config Local Mode**, which allows you to run ICE without any external databases or infrastructure.

## 1. Installation

Install the core engine via pip:

```bash
pip install ice-engine
```

## 2. Basic Configuration

ICE is designed to be invisible. It uses a middleware wrapper to handle memory management automatically.

Create a file named `app.py`:

```python
import asyncio
import os
from openai import AsyncOpenAI
from ice.wrapper import ICEWrapper

async def run_chat():
    # Standard OpenAI client
    raw_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Wrap with ICE - it will automatically use DuckDB for local storage
    # You can specify a custom DB path: ICEWrapper(raw_client, connection_string="my_memory.db")
    client = ICEWrapper(raw_client)

    # First Turn
    print("User: My favorite flavor of ice cream is Mint Chocolate Chip.")
    await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "My favorite flavor of ice cream is Mint Chocolate Chip."}]
    )

    # Second Turn - ICE will automatically recall the flavor
    print("\nUser: What flavor of ice cream do I like?")
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What flavor of ice cream do I like?"}]
    )
    
    print(f"Assistant: {response.choices[0].message.content}")

if __name__ == "__main__":
    asyncio.run(run_chat())
```
