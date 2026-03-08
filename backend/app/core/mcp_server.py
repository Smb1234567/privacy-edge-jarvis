from pathlib import Path
import json
import subprocess
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl
import mcp.server


class JarvisMCPServer:
    def __init__(self):
        self.server = Server("jarvis-mcp")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="read_file",
                    description="Read the contents of a file from the local filesystem",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "The path to the file to read"},
                            "lines": {"type": "integer", "description": "Number of lines to read (default: all)", "default": 100}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="list_directory",
                    description="List files and directories in a given path",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "The directory path to list"},
                            "show_hidden": {"type": "boolean", "description": "Show hidden files", "default": False}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="search_files",
                    description="Search for files by name pattern in a directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {"type": "string", "description": "Directory to search in"},
                            "pattern": {"type": "string", "description": "File name pattern (supports * and ?)"}
                        },
                        "required": ["directory", "pattern"]
                    }
                ),
                Tool(
                    name="grep_search",
                    description="Search for text content within files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {"type": "string", "description": "Directory to search in"},
                            "query": {"type": "string", "description": "Text to search for"},
                            "file_pattern": {"type": "string", "description": "File pattern (e.g., *.py, *.txt)", "default": "*"}
                        },
                        "required": ["directory", "query"]
                    }
                ),
                Tool(
                    name="run_command",
                    description="Execute a shell command and return its output",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The shell command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="get_system_info",
                    description="Get system information (CPU, memory, disk usage)",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_ollama_status",
                    description="Check Ollama LLM service status and available models",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="web_search",
                    description="Search the web using DuckDuckGo",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "description": "Maximum results", "default": 5}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="query_knowledge_base",
                    description="Query the local knowledge base (RAG)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query"},
                            "top_k": {"type": "integer", "description": "Number of results", "default": 5}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_jarvis_status",
                    description="Get the current status of Jarvis assistant (indexed docs, model, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            try:
                if name == "read_file":
                    return await self._read_file(arguments)
                elif name == "list_directory":
                    return await self._list_directory(arguments)
                elif name == "search_files":
                    return await self._search_files(arguments)
                elif name == "grep_search":
                    return await self._grep_search(arguments)
                elif name == "run_command":
                    return await self._run_command(arguments)
                elif name == "get_system_info":
                    return await self._get_system_info()
                elif name == "get_ollama_status":
                    return await self._get_ollama_status()
                elif name == "web_search":
                    return await self._web_search(arguments)
                elif name == "query_knowledge_base":
                    return await self._query_knowledge_base(arguments)
                elif name == "get_jarvis_status":
                    return await self._get_jarvis_status()
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _read_file(self, args: dict) -> list[TextContent]:
        path = Path(args["path"]).expanduser().resolve()
        if not path.exists():
            return [TextContent(type="text", text=f"File not found: {path}")]
        
        lines = args.get("lines", 100)
        try:
            content = path.read_text()
            content_lines = content.split("\n")
            if lines and len(content_lines) > lines:
                content = "\n".join(content_lines[:lines]) + f"\n... ({len(content_lines)} total lines)"
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading file: {e}")]

    async def _list_directory(self, args: dict) -> list[TextContent]:
        path = Path(args["path"]).expanduser().resolve()
        if not path.exists():
            return [TextContent(type="text", text=f"Directory not found: {path}")]
        
        show_hidden = args.get("show_hidden", False)
        try:
            items = []
            for item in sorted(path.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue
                prefix = "📁" if item.is_dir() else "📄"
                items.append(f"{prefix} {item.name}")
            return [TextContent(type="text", text="\n".join(items) if items else "Empty directory")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _search_files(self, args: dict) -> list[TextContent]:
        directory = Path(args["directory"]).expanduser().resolve()
        pattern = args["pattern"]
        
        if not directory.exists():
            return [TextContent(type="text", text=f"Directory not found: {directory}")]
        
        try:
            from glob import glob
            matches = list(directory.rglob(pattern))
            if not matches:
                return [TextContent(type="text", text=f"No files matching '{pattern}' found")]
            
            results = [str(m.relative_to(directory)) for m in matches[:20]]
            return [TextContent(type="text", text="\n".join(results))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _grep_search(self, args: dict) -> list[TextContent]:
        directory = Path(args["directory"]).expanduser().resolve()
        query = args["query"]
        file_pattern = args.get("file_pattern", "*")
        
        if not directory.exists():
            return [TextContent(type="text", text=f"Directory not found: {directory}")]
        
        try:
            import subprocess
            result = subprocess.run(
                ["grep", "-r", "-l", f"--include={file_pattern}", query, str(directory)],
                capture_output=True,
                text=True,
                timeout=30
            )
            files = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if not files:
                return [TextContent(type="text", text=f"No matches found for '{query}'")]
            
            return [TextContent(type="text", text=f"Found in {len(files)} files:\n" + "\n".join(files[:10])]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _run_command(self, args: dict) -> list[TextContent]:
        command = args["command"]
        timeout = args.get("timeout", 30)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout if result.stdout else result.stderr
            return [TextContent(type="text", text=output or "(no output)")]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text=f"Command timed out after {timeout}s")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _get_system_info(self) -> list[TextContent]:
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            info = f"""System Information:
CPU: {cpu}%
RAM: {mem.percent}% ({mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB)
Disk: {disk.percent}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)"""
            return [TextContent(type="text", text=info)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _get_ollama_status(self) -> list[TextContent]:
        try:
            import requests
            res = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            data = res.json()
            models = [m["name"] for m in data.get("models", [])]
            
            if models:
                return [TextContent(type="text", text=f"Ollama is running. Available models:\n" + "\n".join(f"- {m}" for m in models))]
            else:
                return [TextContent(type="text", text="Ollama is running but no models are downloaded")]
        except Exception as e:
            return [TextContent(type="text", text=f"Ollama is not running: {e}")]

    async def _web_search(self, args: dict) -> list[TextContent]:
        query = args["query"]
        max_results = args.get("max_results", 5)
        
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return [TextContent(type="text", text="No results found")]
            
            output = [f"Web search results for '{query}':"]
            for i, r in enumerate(results, 1):
                output.append(f"\n{i}. {r.get('title', 'No title')}")
                output.append(f"   {r.get('href', '')}")
                if r.get("body"):
                    output.append(f"   {r.get('body')[:200]}...")
            
            return [TextContent(type="text", text="\n".join(output))]
        except Exception as e:
            return [TextContent(type="text", text=f"Search error: {e}")]

    async def _query_knowledge_base(self, args: dict) -> list[TextContent]:
        query = args["query"]
        top_k = args.get("top_k", 5)
        
        try:
            from .rag import retrieve
            results = retrieve(query=query, top_k=top_k)
            
            if not results:
                return [TextContent(type="text", text="No relevant documents found")]
            
            output = [f"Found {len(results)} relevant documents:"]
            for i, r in enumerate(results, 1):
                source = r.get("source", "unknown")
                text = r.get("text", "")[:200]
                score = r.get("score", 0)
                output.append(f"\n{i}. [{source}] (score: {score:.2f})")
                output.append(f"   {text}...")
            
            return [TextContent(type="text", text="\n".join(output))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error querying knowledge base: {e}")]

    async def _get_jarvis_status(self) -> list[TextContent]:
        try:
            import requests
            res = requests.get("http://127.0.0.1:8000/api/status", timeout=5)
            data = res.json()
            
            llm = data.get("llm", {})
            index = data.get("index", {})
            
            status = f"""Jarvis Status:
LLM: {llm.get('model', 'unknown')} ({llm.get('status', 'unknown')})
Indexed Documents: {index.get('documents', 0)}
Indexed Chunks: {index.get('chunks', 0)}
Sources: {', '.join(index.get('sources_preview', [])[:3])}"""
            
            return [TextContent(type="text", text=status)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    server = JarvisMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
