import pyfiglet
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def print_banner(console: Console) -> None:
    banner = pyfiglet.figlet_format("VIOSCLAW", font="big")
    mascot = (
        "        [bold yellow]🎓[/bold yellow]\n"
        "      [red]🦞[/red][cyan]🔬[/cyan]\n"
        "    [dim cyan]Edinburgh AI Lab[/dim cyan]\n"
        "   [dim]VIOS Research Group[/dim]"
    )
    table = Table.grid(padding=(0, 6))
    table.add_column(justify="left", vertical="middle")
    table.add_column(justify="left", vertical="middle")
    table.add_row(Text(banner, style="bold cyan"), mascot)
    console.print()
    console.print(
        Panel(
            Align.center(table),
            title="[bold cyan]viosclaw[/bold cyan]",
            subtitle="[dim]Edinburgh AI Lab Agent[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print(
        Align.center(
            "[dim]type [bold white]exit[/bold white] to quit  |  "
            "type [bold white]/help[/bold white] for commands[/dim]"
        )
    )
    console.print(
        Align.center("[bold magenta]WORKDIR: [/bold magenta] [underline blue]")
    )
    console.print()
