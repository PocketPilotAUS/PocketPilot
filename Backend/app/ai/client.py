import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def generate_ai_explanation(prompt):
    ollama_url = os.getenv("OLLAMA_URL")

    if not ollama_url:
        raise ValueError("OLLAMA_URL is not configured.")

    client = OpenAI(
        base_url=ollama_url,
        api_key="ollama",
        timeout=120.0
    )

    response = client.chat.completions.create(
        model="qwen3:4b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are PocketPilot, a personal finance assistant. "
                    "Explain verified financial information clearly. "
                    "Do not invent amounts, percentages, or balances. "
                    "Do not assume why spending changed. "
                    "Keep explanations short and practical."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        extra_body={"think": False}
    )

    return response.choices[0].message.content