import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__

app = typer.Typer(name="vioscope", help="VioScope research CLI")

console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Entry point for the VioScope CLI.

    Shows a minimal welcome panel until subcommands are added in later stories.
    """

    if ctx.invoked_subcommand is not None:
        return

    console.print(
        Panel(
            f"VioScope CLI is ready. Version {__version__}.\nUse --help to see available commands.",
            title="VioScope",
            expand=False,
        )
    )
    raise typer.Exit()


if __name__ == "__main__":
    app()
