"""ANSI color constants mapped from design tokens."""

from rich.theme import Theme

ANSI = {
    "ok": "\x1b[32m",
    "warn": "\x1b[33m",
    "err": "\x1b[31m",
    "info": "\x1b[36m",
    "reset": "\x1b[0m",
    "dim": "\x1b[2m",
    "bold": "\x1b[1m",
}

RICH_THEME = Theme({
    "ok": "bold green",
    "warn": "bold yellow",
    "err": "bold red",
    "info": "bold cyan",
    "muted": "dim white",
    "escalated": "bold yellow",
    "replied": "bold green",
    "invalid": "dim",
    "area": "cyan",
})

STATUS_SYMBOL = {
    "replied": "[ok]✓[/ok]",
    "escalated": "[warn]↑[/warn]",
    "failed": "[err]✗[/err]",
}
