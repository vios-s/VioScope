from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from vioscope import __version__
from vioscope.config import ConfigError, VioScopeConfig, create_default_config, load_config
from vioscope.core.ui import console
from vioscope.kb import LocalKB

_create_default_config = create_default_config

app = typer.Typer(name="vioscope", help="VioScope research CLI", add_completion=False)
config_app = typer.Typer(name="config", help="Configuration commands", add_completion=False)
kb_app = typer.Typer(name="kb", help="Knowledge base operations", add_completion=False)


def _effective_config_path(ctx: typer.Context, override: Path | None) -> Path | None:
    if override is not None:
        return override
    ctx.obj = ctx.obj or {}
    value = ctx.obj.get("config_path")
    return value if isinstance(value, Path) else None


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


def _build_local_kb(cfg: VioScopeConfig) -> LocalKB:
    kb_root: Path | None = None
    if cfg.knowledge_base and isinstance(cfg.knowledge_base.get("local_path"), str):
        kb_root = Path(str(cfg.knowledge_base["local_path"])).expanduser()
    return LocalKB(kb_root)


@kb_app.command("list", help="List local KB records")
def kb_list(
    ctx: typer.Context,
    record_type: str = typer.Option("", "--type", help="Optional record type filter"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    kb = _build_local_kb(cfg)
    records = kb.list_records(record_type or None)

    table = Table(title="Knowledge Base Records")
    table.add_column("Record ID")
    table.add_column("Type")
    table.add_column("Session")
    table.add_column("Created At")
    for record in records:
        table.add_row(
            str(record.get("record_id", "")),
            str(record.get("record_type", "")),
            str(record.get("session_id", "")),
            str(record.get("created_at", "")),
        )
    console.print(table)


@kb_app.command("show", help="Show a stored KB record")
def kb_show(
    ctx: typer.Context,
    record_type: str = typer.Argument(..., help="Record type"),
    record_id: str = typer.Argument(..., help="Record id"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    kb = _build_local_kb(cfg)
    content = kb.read_record(record_type, record_id)
    console.print(Panel(content, title=f"{record_type}:{record_id}", expand=False))


@kb_app.command("search", help="Search the local KB")
def kb_search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", min=1, help="Maximum results"),
    record_types: list[str] | None = typer.Option(
        None, "--type", help="Optional record type filters"
    ),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    cfg = _load_and_validate(ctx, config)
    kb = _build_local_kb(cfg)
    results = kb.search(
        query=query,
        limit=limit,
        record_types=tuple(record_types) if record_types else None,
    )

    table = Table(title=f"KB Search: {query}")
    table.add_column("Type")
    table.add_column("Session")
    table.add_column("Record ID")
    table.add_column("Snippet")
    for record in results:
        table.add_row(
            record.record_type,
            record.session_id,
            record.record_id,
            record.content_snippet.replace("\n", " "),
        )
    console.print(table)


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
            _create_default_config(config_path)
        except ConfigError as exc:
            console.print(f"[red]Configuration error:[/red] {exc}")
            raise typer.Exit(code=1)

    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1)

    if config_path is not None:
        path_text = str(config_path)
    else:
        path_text = (
            "~/.vioscope/config.yaml layered over {PROJ_DIR}/.vioscope/config.yaml when present"
        )
    console.print(
        Panel(
            f"Configuration initialized or loaded at {path_text}. Provider={cfg.model.provider}",
            title="Config",
            expand=False,
        )
    )


app.add_typer(config_app, name="config")
app.add_typer(kb_app, name="kb")


if __name__ == "__main__":  # pragma: no cover
    app()
