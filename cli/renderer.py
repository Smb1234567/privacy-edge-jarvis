import sys
import threading
import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.console import ConsoleRenderable
from rich.style import Style
from rich import box


console = Console()


class LoadingState:
    def __init__(self, message: str = "Thinking"):
        self.message = message
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._current_frame = 0

    def _animate(self):
        while not self._stop_event.is_set():
            frame = self._spinner_frames[self._current_frame]
            sys.stdout.write(f"\r{frame} {self.message}...")
            sys.stdout.flush()
            self._current_frame = (self._current_frame + 1) % len(self._spinner_frames)
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.message) + 10))
        sys.stdout.flush()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self, final_message: Optional[str] = None):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        if final_message:
            sys.stdout.write(f"\r✓ {final_message}\n")
            sys.stdout.flush()


def print_header():
    console.print("\n[bold cyan]🔒[/bold cyan] [bold]Privacy Edge Jarvis[/bold]\n")


def print_user_message(query: str):
    console.print(f"[bold green]▸ You[/bold green]")
    console.print(f"  {query}\n")


def print_thinking():
    console.print("[dim]🤔 Thinking...[/dim]", end="")


def print_thinking_stop():
    console.print(" [green]✓[/green]\n")


def print_searching_knowledge():
    console.print("[dim]🔍 Searching knowledge base...[/dim]", end="")


def print_searching_stop():
    console.print(" [green]✓[/green]\n")


def print_calling_tool(tool_name: str):
    console.print(f"[dim]🔧 Calling tool: {tool_name}...[/dim]", end="")


def print_tool_stop():
    console.print(" [green]✓[/green]\n")


def print_assistant_streaming(text: str):
    console.print(text, end="")


def print_tool_trace(tools: list[dict]):
    if not tools:
        return

    table = Table(
        title="[bold]🛠️ Tool Trace[/bold]",
        box=box.ROUNDED,
        show_header=False,
    )
    table.add_column("tool", style="cyan")
    table.add_column("status", style="white")

    for t in tools:
        tool_name = t.get("tool", "unknown")
        status = t.get("status", "unknown")
        hits = t.get("hits")
        rows = t.get("rows")

        status_str = f"[green]✓[/green] {status}"
        if hits is not None:
            status_str += f" • {hits} hits"
        if rows is not None:
            status_str += f" • {rows} rows"

        table.add_row(f"🔧 {tool_name}", status_str)

    console.print(table)


def print_citations(citations: list[dict]):
    if not citations:
        console.print("[dim]No citations[/dim]")
        return

    table = Table(
        title="[bold]📄 Citations[/bold]",
        box=box.ROUNDED,
        show_header=False,
    )
    table.add_column("source", style="blue")
    table.add_column("chunk", style="dim")
    table.add_column("score", style="yellow")

    for c in citations:
        source = c.get("source", "unknown")
        chunk = c.get("chunk_id", "?")
        score = f"{c.get('score', 0):.2f}"
        table.add_row(source.split("/")[-1], chunk, score)

    console.print(table)


def print_latency(latency_ms: float, llm_info: dict):
    model = llm_info.get("model", "unknown")
    provider = llm_info.get("provider", "unknown")
    status = llm_info.get("status", "unknown")

    status_color = "green" if status == "ok" else "yellow"
    console.print(f"\n[dim]⏱️ {latency_ms}ms[/dim] • [dim]{provider}/{model}[/dim] • [{status_color}]{status}[/{status_color}]")


def print_callout(title: str, message: str, style: str = "info"):
    colors = {
        "info": ("blue", "ℹ️"),
        "warning": ("yellow", "⚠️"),
        "error": ("red", "❌"),
        "success": ("green", "✓"),
    }
    color, icon = colors.get(style, ("blue", "ℹ️"))
    console.print(f"[{color}]{icon}[/{color}] [{color}bold]{title}[/{color}bold]: {message}")


def render_markdown(text: str) -> None:
    lines = text.split("\n")
    in_code_block = False
    code_content = []
    code_language = ""

    for line in lines:
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_language = line[3:].strip()
                code_content = []
            else:
                in_code_block = False
                if code_content:
                    syntax = Syntax("\n".join(code_content), code_language or "text", theme="monokai", line_numbers=True)
                    console.print(syntax)
                code_content = []
                code_language = ""
            continue

        if in_code_block:
            code_content.append(line)
            continue

        if line.strip().startswith("- ") or line.strip().startswith("* "):
            console.print(f"  {line}")
        elif line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            console.print(f"  {line}")
        elif line.startswith("# "):
            console.print(f"[bold]{line[2:]}[/bold]")
        elif line.startswith("## "):
            console.print(f"[bold]{line[3:]}[/bold]")
        elif line.startswith("### "):
            console.print(f"[bold]{line[4:]}[/bold]")
        elif line.strip():
            console.print(line)
        else:
            console.print()


def print_error(msg: str):
    print_callout("Error", msg, "error")


def print_warning(msg: str):
    print_callout("Warning", msg, "warning")


def print_info(msg: str):
    print_callout("Info", msg, "info")


def print_success(msg: str):
    print_callout("Success", msg, "success")


def print_status_panel(status: dict):
    llm = status.get("llm", {})
    index = status.get("index", {})

    table = Table(title="[bold]System Status[/bold]", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    llm_status = llm.get("status", "unknown")
    llm_color = "green" if llm_status == "ok" else "red"

    table.add_row("Model", f"{llm.get('model', 'N/A')}")
    table.add_row("LLM Status", f"[{llm_color}]{llm_status}[/{llm_color}]")
    table.add_row("Indexed Docs", str(index.get("documents", 0)))
    table.add_row("Indexed Chunks", str(index.get("chunks", 0)))

    console.print(table)


def print_metrics(metrics: dict):
    table = Table(title="[bold]Runtime Metrics[/bold]", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Process RSS", f"{metrics.get('process_rss_mb', 0)} MB")
    table.add_row("CPU", f"{metrics.get('cpu_percent', 0)}%")
    table.add_row("RAM", f"{metrics.get('ram_percent', 0)}%")

    console.print(table)


def clear_screen():
    console.clear()
    print_header()
