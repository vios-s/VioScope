from typing import cast

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from .. import config


class Message(BaseModel):
    role: str
    content: str


client = openai.OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
)


def run_agent() -> None:
    messages: list[Message] = [
        Message(role="system", content="You are a helpful assistant.")
    ]
    while True:
        # 1. get user input
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        # 2. append to messages
        messages.append(Message(role="user", content=user_input))
        messages_payload = cast(
            list[ChatCompletionMessageParam], [m.model_dump() for m in messages]
        )

        # 3. send to LLM
        response = client.chat.completions.create(
            model=config.OPENROUTER_DEFAULT_MODEL,
            messages=messages_payload,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )

        # 4. print response
        assistant_message = response.choices[0].message
        print(f"Assistant: {assistant_message.content}")

        # 5. append response to messages
        messages.append(
            Message(
                role=assistant_message.role, content=assistant_message.content or ""
            )
        )
