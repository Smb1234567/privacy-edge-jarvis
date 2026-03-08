import asyncio
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings

from .client import APIClient, check_api_status
from .renderer import (
    console,
    print_header,
    print_user_message,
    print_tool_trace,
    print_citations,
    print_latency,
    render_markdown,
    print_error,
    print_warning,
    print_info,
    print_success,
    print_status_panel,
    print_metrics,
    clear_screen,
    print_thinking,
    print_thinking_stop,
    print_searching_knowledge,
    print_searching_stop,
)


style = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "default": "ansigreen",
    }
)

kb = KeyBindings()


@kb.add("c-c")
def _(event):
    event.app.exit(result=None)


@kb.add("c-l")
def _(event):
    clear_screen()


class JarvisCLI:
    def __init__(self):
        self.client = APIClient()
        self.history_file = Path.home() / ".jarvis_history"
        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=kb,
            style=style,
        )

    async def cleanup(self):
        await self.client.close()

    async def check_connection(self) -> bool:
        console.print("[dim]Connecting to API...[/dim]")
        if await check_api_status():
            console.print("[green]✓[/green] Connected to API\n")
            return True
        console.print("[red]✗[/red] Cannot connect to API at http://127.0.0.1:8000")
        console.print("[dim]Start the backend with: cd backend && uvicorn app.main:app --reload[/dim]\n")
        return False

    async def show_status(self):
        try:
            status = await self.client.get_status()
            print_status_panel(status)
        except Exception as e:
            print_error(f"Failed to get status: {e}")

    async def show_metrics(self):
        try:
            metrics = await self.client.get_metrics()
            print_metrics(metrics)
        except Exception as e:
            print_error(f"Failed to get metrics: {e}")

    async def handle_upload(self, files: list[str]):
        console.print(f"[dim]Uploading {len(files)} file(s)...[/dim]")
        try:
            result = await self.client.upload_files(files)
            print_success(f"Indexed {result.get('indexed', {}).get('documents_indexed', 0)} docs, {result.get('indexed', {}).get('chunks_indexed', 0)} chunks")
        except Exception as e:
            print_error(f"Upload failed: {e}")

    async def handle_query(self, query: str):
        print_user_message(query)

        tool_trace = []
        citations = []
        answer_text = ""
        latency_ms = 0
        llm_info = {}
        first_token_received = False

        print_thinking()

        try:
            async for event in self.client.chat_stream(query):
                event_type = event.get("type")

                if event_type == "meta":
                    print_thinking_stop()
                    tool_trace = event.get("tool_trace", [])
                    citations = event.get("citations", [])
                    llm_info = event.get("llm", {})
                    if tool_trace:
                        print_searching_knowledge()
                        print_searching_stop()
                    console.print()

                elif event_type == "token":
                    if not first_token_received:
                        first_token_received = True
                        console.print()

                    token = event.get("token", "")
                    answer_text += token
                    console.print(token, end="")
                    console.file.flush()

                elif event_type == "done":
                    latency_ms = event.get("latency_ms", 0)
                    llm_info = event.get("llm", {})

                elif event_type == "error":
                    print_thinking_stop()
                    print_error(event.get("error", "Unknown error"))
                    return

        except Exception as e:
            print_thinking_stop()
            print_error(f"Request failed: {e}")
            return

        if not first_token_received:
            print_thinking_stop()

        console.print()

        if tool_trace:
            print_tool_trace(tool_trace)

        if citations:
            print_citations(citations)

        if latency_ms or llm_info:
            print_latency(latency_ms or 0, llm_info or {})

    async def run(self):
        print_header()

        if not await self.check_connection():
            return

        await self.show_status()

        console.print("\n[dim]Commands:[/dim]")
        console.print("  [cyan]:status[/cyan]   - Show system status")
        console.print("  [cyan]:metrics[/cyan]  - Show runtime metrics")
        console.print("  [cyan]:upload <files>[/cyan] - Upload files to knowledge base")
        console.print("  [cyan]:clear[/cyan]    - Clear screen")
        console.print("  [cyan]:help[/cyan]     - Show this help")
        console.print("  [cyan]Ctrl+L[/cyan]    - Clear screen")
        console.print("  [cyan]Ctrl+C[/cyan]    - Exit")
        console.print()

        while True:
            try:
                user_input = await self.session.prompt_async("> ")
            except KeyboardInterrupt:
                console.print("\n[dim]Use Ctrl+C to exit[/dim]")
                continue
            except EOFError:
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith(":"):
                cmd = user_input[1:].split()
                command = cmd[0].lower() if cmd else ""
                args = cmd[1:]

                if command in ("exit", "quit", "q"):
                    break
                elif command in ("help", "h", "?"):
                    console.print("\n[dim]Commands:[/dim]")
                    console.print("  [cyan]:status[/cyan]   - Show system status")
                    console.print("  [cyan]:metrics[/cyan]  - Show runtime metrics")
                    console.print("  [cyan]:upload <files>[/cyan] - Upload files")
                    console.print("  [cyan]:clear[/cyan]    - Clear screen")
                    console.print("  [cyan]:help[/cyan]     - Show help")
                    console.print()
                elif command == "clear":
                    clear_screen()
                elif command == "status":
                    await self.show_status()
                elif command == "metrics":
                    await self.show_metrics()
                elif command == "upload":
                    if args:
                        await self.handle_upload(args)
                    else:
                        print_warning("Usage: :upload <file1> <file2> ...")
                else:
                    print_warning(f"Unknown command: {command}")
                continue

            await self.handle_query(user_input)

        await self.cleanup()


async def main():
    cli = JarvisCLI()
    try:
        await cli.run()
    except KeyboardInterrupt:
        pass
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
