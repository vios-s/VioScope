import json

import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .. import config
from .banner import print_banner
from .tools import TOOL_HANDLERS, TOOLS

client = openai.OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
)


def run_agent() -> None:
    # Init console for rich output
    console = Console()

    print_banner(console)

    messages: list[dict] = [{"role": "system", "content": "You are a helpful assistant."}]

    # outer loop: wait for user input
    while True:
        console.print("[bold cyan]You >[/bold cyan] ", end="")
        user_input = input()
        if user_input.lower() in ["exit", "quit"]:
            console.print("[dim]Goodbye![/dim]")
            break

        messages.append({"role": "user", "content": user_input})

        # inner loop: LLM + tool dispatch (no user input here)
        while True:
            try:
                with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                    response = client.chat.completions.create(
                        model=config.OPENROUTER_DEFAULT_MODEL,
                        messages=messages,
                        max_tokens=config.MAX_TOKENS,
                        temperature=config.TEMPERATURE,
                        tools=TOOLS,
                    )
            except Exception as e:
                console.print(f"[bold red]API Error:[/bold red] {str(e)}")
                messages.pop()  # remove user message if API call fails
                break

            assistant_response = response.choices[0]
            finish_reason = assistant_response.finish_reason

            # always append assistant message to history
            messages.append(assistant_response.message.model_dump(exclude_unset=True))

            if finish_reason == "stop":
                console.print(
                    Panel(
                        Markdown(assistant_response.message.content or ""),
                        title="Assistant",
                    )
                )
                break
            elif finish_reason == "length":
                console.print(
                    Panel(
                        Markdown((assistant_response.message.content or "") + "..."),
                        title="Assistant (truncated)",
                    )
                )
                break
            elif finish_reason == "tool_calls":
                # TODO: execute tools and append results to messages, then continue
                # 1. go through `assistant_response.message.tool_calls` list
                for tool_call in assistant_response.message.tool_calls or []:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    console.print(
                        f"[bold yellow]Tool call:[/bold yellow] {tool_name}({tool_args})"
                    )

                    # 2. for each tool call, find the handler in TOOL_HANDLERS
                    # and execute it
                    result = TOOL_HANDLERS[tool_name](**json.loads(tool_args))

                    # 3. append tool results to messages with role "tool"
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result,
                        }
                    )
                continue
