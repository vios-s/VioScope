from typing import cast

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .. import config
from .banner import print_banner


class Message(BaseModel):
    role: str
    content: str


client = openai.OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
)


def run_agent() -> None:
    # Init console for rich output
    console = Console()

    print_banner(console)

    messages: list[Message] = [
        Message(role="system", content="You are a helpful assistant.")
    ]
    while True:
        # 1. get user input
        console.print("[bold cyan]You >[/bold cyan] ", end="")
        user_input = input()
        if user_input.lower() in ["exit", "quit"]:
            console.print("[dim]Goodbye![/dim]")
            break
        # 2. append to messages
        messages.append(Message(role="user", content=user_input))
        messages_payload = cast(
            list[ChatCompletionMessageParam], [m.model_dump() for m in messages]
        )

        # 3. send to LLM
        try:
            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = client.chat.completions.create(
                    model=config.OPENROUTER_DEFAULT_MODEL,
                    messages=messages_payload,
                    max_tokens=config.MAX_TOKENS,
                    temperature=config.TEMPERATURE,
                )
        except Exception as e:
            console.print(f"[bold red]API Error:[/bold red] {str(e)}")
            messages.pop()  # remove user message if API call fails
            continue

        # 4. print response
        assistant_response = response.choices[0]
        finish_reason = assistant_response.finish_reason

        if finish_reason == "stop":
            console.print(
                Panel(
                    Markdown(assistant_response.message.content or ""),
                    title="Assistant",
                )
            )
        elif finish_reason == "length":
            if assistant_response.message.content is not None:
                console.print(
                    Panel(
                        Markdown(
                            "Partial response (truncated): "
                            + assistant_response.message.content
                            + "..."
                        ),
                        title="Assistant (truncated)",
                    )
                )
            else:
                console.print(
                    Panel(
                        Markdown("Response truncated due to length."),
                        title="Assistant (truncated)",
                    )
                )
        elif finish_reason == "tool_calls":
            # TODO: handle tool calls
            pass

        # 5. append response to messages
        messages.append(
            Message(
                role=assistant_response.message.role,
                content=assistant_response.message.content or "",
            )
        )
