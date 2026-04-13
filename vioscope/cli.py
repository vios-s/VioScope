from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from vioscope import __version__
from vioscope.config import ConfigError, VioScopeConfig, create_default_config, load_config
from vioscope.core.ui import console

app = typer.Typer(name="vioscope", help="VioScope research CLI", add_completion=False)
config_app = typer.Typer(name="config", help="Configuration commands", add_completion=False)


def _effective_config_path(ctx: typer.Context, override: Path | None) -> Path | None:
    if override is not None:
        return override
    ctx.obj = ctx.obj or {}
    return ctx.obj.get("config_path")


def _load_and_validate(ctx: typer.Context, override_path: Path | None = None) -> VioScopeConfig:
    config_path = _effective_config_path(ctx, override_path)
    try:
        return load_config(config_path)
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    ctx.obj = ctx.obj or {}
    ctx.obj["config_path"] = config

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


@app.command(help="Run full research workflow")
def research(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Research question"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    console.print(
        Panel(
            f"Research command is not yet implemented.\nQuestion: {question}\nModel: {cfg.model.provider}:{cfg.model.model_id}",
            title="Research",
            expand=False,
        )
    )


@app.command(help="Search literature only")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    console.print(
        Panel(
            f"Search command is not yet implemented.\nQuery: {query}\nModel: {cfg.model.provider}:{cfg.model.model_id}",
            title="Search",
            expand=False,
        )
    )


@app.command(help="Review existing artifacts")
def review(
    ctx: typer.Context,
    source: str = typer.Option("", "--from-kb", help="KB entry id to review"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    from_text = f"from KB id {source}" if source else "(no source specified)"
    console.print(
        Panel(
            f"Review command is not yet implemented.\nSource: {from_text}\nModel: {cfg.model.provider}:{cfg.model.model_id}",
            title="Review",
            expand=False,
        )
    )


@app.command(help="Draft or outline writing tasks")
def write(
    ctx: typer.Context,
    template: str = typer.Option(
        "", "--template", help="Journal template (e.g., neurips, nature)"
    ),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    template_text = template or "(no template specified)"
    console.print(
        Panel(
            f"Write command is not yet implemented.\nTemplate: {template_text}\nModel: {cfg.model.provider}:{cfg.model.model_id}",
            title="Write",
            expand=False,
        )
    )


@app.command(help="Knowledge base operations")
def kb(
    ctx: typer.Context,
    action: str = typer.Option("list", "--action", help="KB action (list/show/sync)"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    console.print(
        Panel(
            f"KB command is not yet implemented.\nAction: {action}\nModel: {cfg.model.provider}:{cfg.model.model_id}",
            title="KB",
            expand=False,
        )
    )


@config_app.command("validate", help="Validate configuration")
def config_validate(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    console.print(
        Panel(
            f"Configuration ok. Provider={cfg.model.provider}, Model={cfg.model.model_id}",
            title="Config",
            expand=False,
        )
    )


@config_app.command("init", help="Create or load default config")
def config_init(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    config_path = config
    if config_path is not None and not config_path.exists():
        try:
            create_default_config(config_path)
        except ConfigError as exc:
            console.print(f"[red]Configuration error:[/red] {exc}")
            raise typer.Exit(code=1)

    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1)

    path_text = str(config_path if config_path is not None else "~/.vioscope/config.yaml")
    console.print(
        Panel(
            f"Configuration initialized or loaded at {path_text}. Provider={cfg.model.provider}",
            title="Config",
            expand=False,
        )
    )


app.add_typer(config_app, name="config")


if __name__ == "__main__":  # pragma: no cover
    app()
