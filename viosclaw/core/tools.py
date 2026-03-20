import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from .ui import console

WORKDIR = Path.cwd()


def print_tool(tool_name: str, args: dict) -> None:
    """Prints a tool call in a formatted way."""
    console.print(f"[dim][tool: {tool_name}] {args}[/dim]")


def safe_path(raw: str) -> Path:
    """
    Resolves a raw path to an absolute path within the workspace directory, preventing directory traversal attacks.
    """
    target = (WORKDIR / raw).resolve()
    if not str(target).startswith(str(WORKDIR)):
        raise ValueError("Unsafe path detected: " + raw)
    return target


def tool_read_file(file_path: str) -> str:
    """Reads the content of a file."""
    print_tool("read_file", {"file_path": file_path})

    try:
        with open(safe_path(file_path), "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def tool_write_file(file_path: str, content: str) -> str:
    """Writes content to a file."""
    print_tool("write_file", {"file_path": file_path, "content": content})

    try:
        target = safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)  # ensure parent directories exist
        with open(target, "w") as f:
            f.write(content)
        return "File written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"


def tool_run_python(code: str) -> str:
    """Runs Python code and returns the output."""
    print_tool("run_python", {"code": code})

    try:
        # WARNING: using subprocess to run code can be dangerous. In a real implementation, consider using a sandboxed environment.
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10,  # prevent long-running code
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]:\n{result.stderr}"
        if result.returncode != 0:
            return f"Error running code: {output}"
        return output
    except Exception as e:
        return f"Error running code: {str(e)}"


def tool_search_arxiv(query: str) -> str:
    """Searches arXiv for papers matching the query and returns a summary."""
    print_tool("search_arxiv", {"query": query})
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results=5"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"Error searching arXiv: {str(e)}"


TOOL_HANDLERS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "run_python": tool_run_python,
    "search_arxiv": tool_search_arxiv,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read, relative to the workspace directory.",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write, relative to the workspace directory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Runs Python code and returns the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to run.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": "Searches arXiv for papers matching the query and returns a summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for arXiv.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]
