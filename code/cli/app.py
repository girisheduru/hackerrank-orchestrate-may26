"""Typer CLI application for the support triage agent."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from cli.theme import RICH_THEME, STATUS_SYMBOL

app = typer.Typer(
    name="triage",
    help="Multi-domain support triage agent (HackerRank · Claude · Visa)",
    add_completion=False,
)
console = Console(theme=RICH_THEME)
err_console = Console(stderr=True, theme=RICH_THEME)


def _resolve_path(env_var: str, default: str, override: Optional[str]) -> Path:
    if override:
        return Path(override)
    return Path(os.environ.get(env_var, default))


@app.command("run")
def run_cmd(
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Input CSV path"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output CSV path"),
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Corpus data directory"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Process only N tickets"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Override company for all tickets"),
    tail: bool = typer.Option(False, "--tail", help="Stream progress to terminal"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate pipeline only, no output written"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Deterministic seed"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose structured logs on stderr"),
):
    """Process support tickets in batch and write output CSV."""
    from orchestrator.pipeline import TriagePipeline
    from ticket_io.csv_reader import read_tickets
    from ticket_io.csv_writer import write_results

    input_path = _resolve_path("TRIAGE_INPUT_CSV", "support_tickets/support_tickets.csv", input)
    output_path = _resolve_path("TRIAGE_OUTPUT_CSV", "support_tickets/output.csv", output)
    data_path = _resolve_path("TRIAGE_DATA_DIR", "data", data_dir)

    if not input_path.exists():
        err_console.print(f"[err]Input file not found: {input_path}[/err]")
        raise typer.Exit(code=3)

    if not data_path.exists():
        err_console.print(f"[err]Data directory not found: {data_path}[/err]")
        raise typer.Exit(code=8)

    if not json_output:
        console.print(f"[info]Loading corpus from {data_path} …[/info]")

    pipeline = TriagePipeline(
        data_dir=data_path,
        seed=seed,
        verbose=verbose,
    )

    tickets = read_tickets(input_path)
    if limit:
        tickets = tickets[:limit]

    if not json_output:
        console.print(f"[muted]job_id={pipeline.job_id}  tickets={len(tickets)}[/muted]")

    results = []

    if tail and not json_output:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Triaging tickets…", total=len(tickets))
            for ticket in tickets:
                if company:
                    ticket.company = company
                result = pipeline.process_ticket(ticket)
                results.append(result)
                sym = STATUS_SYMBOL.get(result.status, "?")
                progress.console.print(
                    f"  {sym} row={result.row_id:>2d}  "
                    f"[area]{result.product_area}[/area]  "
                    f"[muted]{result.request_type}[/muted]"
                )
                progress.advance(task)
    else:
        for ticket in tickets:
            if company:
                ticket.company = company
            result = pipeline.process_ticket(ticket)
            results.append(result)

    if dry_run:
        if not json_output:
            console.print("[warn]Dry run — no output written[/warn]")
        raise typer.Exit(code=0)

    write_results(results, output_path)

    if json_output:
        import json
        summary = {
            "job_id": pipeline.job_id,
            "status": "completed",
            "total_rows": len(results),
            "replied_count": sum(1 for r in results if r.status == "replied"),
            "escalated_count": sum(1 for r in results if r.status == "escalated"),
            "output_csv": str(output_path),
        }
        print(json.dumps(summary, indent=2))
    else:
        replied = sum(1 for r in results if r.status == "replied")
        escalated = sum(1 for r in results if r.status == "escalated")
        console.print(
            f"\n[ok]Done[/ok]  replied={replied}  "
            f"[warn]escalated[/warn]={escalated}  "
            f"output={output_path}"
        )


@app.command("status")
def status_cmd(
    job_id: Optional[str] = typer.Argument(None, help="Job ID to inspect"),
):
    """Show job metadata from last run."""
    from store.persistence import RunStore
    store = RunStore()
    run = store.load_latest() if not job_id else store.load(job_id)
    if not run:
        console.print("[warn]No run found[/warn]")
        raise typer.Exit(code=1)

    table = Table(title=f"Job {run['job_id']}", show_lines=True)
    table.add_column("Field")
    table.add_column("Value")
    for k, v in run.items():
        table.add_row(str(k), str(v))
    console.print(table)


@app.command("logs")
def logs_cmd(
    job_id: Optional[str] = typer.Argument(None),
    level: str = typer.Option("info", "--level"),
    follow: bool = typer.Option(False, "--follow", "-f"),
):
    """Show structured logs from a run."""
    from store.persistence import RunStore
    store = RunStore()
    log_path = store.log_path(job_id)
    if not log_path or not log_path.exists():
        console.print("[warn]No log file found[/warn]")
        raise typer.Exit(1)
    for line in log_path.read_text().splitlines():
        console.print(line)


@app.command("config")
def config_cmd(
    show: bool = typer.Option(False, "--show"),
    validate: bool = typer.Option(False, "--validate"),
):
    """Show effective configuration."""
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not cfg_path.exists():
        console.print("[warn]No config file found[/warn]")
        return
    cfg = yaml.safe_load(cfg_path.read_text())
    console.print_json(data=cfg)
