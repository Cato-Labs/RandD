"""Discovery tool for the installed Strands tool libraries.

Gives load_tool runtime access to the three installed tool libraries:
- strands_tools (strands-agents-tools)
- strands_fun_tools (strands-fun-tools)
- strands_google (strands-google)

load_tool loads a tool from a Python file path. Library tools live inside
installed packages, so this module enumerates each library's tool modules and
returns the exact ``name`` + ``path`` arguments to pass to load_tool.
"""

import importlib
import pkgutil
from typing import Any

from strands import tool
from strands.tools.decorator import DecoratedFunctionTool

TOOL_LIBRARIES = {
    "strands_tools": "strands-agents-tools (agent tools: calculator, python_repl, file ops, AWS, and more)",
    "strands_fun_tools": "strands-fun-tools (creative/utility tools: chess, clipboard, template, utility, and more)",
    "strands_google": "strands-google (Google APIs: use_google, google_auth, gmail_send, gmail_reply)",
}


def _module_tools(module: Any) -> list[str]:
    """Return the tool names defined in a module (TOOL_SPEC or @tool styles)."""
    names = []
    tool_spec = getattr(module, "TOOL_SPEC", None)
    if isinstance(tool_spec, dict) and tool_spec.get("name"):
        names.append(tool_spec["name"])
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, DecoratedFunctionTool):
            names.append(attr.tool_name)
    return sorted(set(names))


def _describe_library(library: str) -> list[str]:
    lines = [f"# {library} — {TOOL_LIBRARIES[library]}"]
    package = importlib.import_module(library)
    for info in sorted(pkgutil.iter_modules(package.__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        module_path = f"{library}.{info.name}"
        try:
            module = importlib.import_module(module_path)
        except Exception as e:  # missing optional extra, hardware, etc.
            lines.append(f"- {info.name}: UNAVAILABLE ({type(e).__name__}: {e})")
            continue
        tool_names = _module_tools(module)
        if not tool_names:
            continue
        for tool_name in tool_names:
            lines.append(f"- {tool_name}: load_tool(name=\"{tool_name}\", path=\"{module.__file__}\")")
    return lines


@tool
def list_library_tools(library: str | None = None) -> str:
    """List loadable tools from the installed Strands tool libraries.

    Enumerates the tool modules in strands_tools (strands-agents-tools),
    strands_fun_tools, and strands_google, returning for each tool the exact
    name and file path to pass to load_tool. Tools whose optional dependencies
    are not installed are reported as UNAVAILABLE with the reason.

    Args:
        library: Optional library to list ("strands_tools", "strands_fun_tools",
            or "strands_google"). Lists all three libraries when omitted.

    Returns:
        str: One line per tool in the form
            ``- tool_name: load_tool(name="tool_name", path="/abs/path.py")``.
    """
    if library is not None and library not in TOOL_LIBRARIES:
        return f"Unknown library '{library}'. Available: {', '.join(TOOL_LIBRARIES)}"

    libraries = [library] if library else list(TOOL_LIBRARIES)
    lines: list[str] = []
    for lib in libraries:
        try:
            lines.extend(_describe_library(lib))
        except Exception as e:
            lines.append(f"# {lib}: failed to enumerate ({type(e).__name__}: {e})")
        lines.append("")
    return "\n".join(lines).strip()
