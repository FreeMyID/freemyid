"""Keep the developer CLI reference aligned with the registered Typer command tree."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import typer.main

from freemyid.cli import app

ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = ROOT / "src/freemyid/cli.py"
JSON_PATH = ROOT / "web/src/pages/developers/cli/_commands.json"
PAGE_PATH = ROOT / "web/src/pages/developers/cli/index.astro"
CLI_SOURCE = "src/freemyid/cli.py"


def _functions() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    module = ast.parse(CLI_PATH.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _source_line(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str | None = None) -> str:
    if name is not None:
        args = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
        if function.args.vararg:
            args.append(function.args.vararg)
        if function.args.kwarg:
            args.append(function.args.kwarg)
        for arg in args:
            if arg.arg == name:
                return f"{CLI_SOURCE}:{arg.lineno}"
    if function.decorator_list:
        return f"{CLI_SOURCE}:{function.decorator_list[0].lineno}"
    return f"{CLI_SOURCE}:{function.lineno}"


def _short_help(command: Any) -> str:
    return next((line.strip() for line in (command.help or "").splitlines() if line.strip()), "")


def _visible(group: Any) -> dict[str, Any]:
    return {
        name: command
        for name, command in group.commands.items()
        if not getattr(command, "hidden", False)
    }


def _commands(root: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, command in _visible(root).items():
        current_path = (*path, name)
        if hasattr(command, "commands") and hasattr(command, "list_commands"):
            result.extend(_commands(command, current_path))
            continue

        callback = command.callback
        function = _functions()[callback.__name__]
        source = _source_line(function)
        doc = ast.get_docstring(function, clean=False)
        summary_source = ""
        if doc and function.body and isinstance(function.body[0], ast.Expr):
            summary_source = f"{CLI_SOURCE}:{function.body[0].lineno}"

        arguments: list[dict[str, Any]] = []
        options: list[dict[str, Any]] = []
        for parameter in command.params:
            argument_source = _source_line(function, parameter.name)
            if parameter.__class__.__name__ == "TyperOption":
                options.append(
                    {
                        "flags": list(parameter.opts)
                        + list(getattr(parameter, "secondary_opts", [])),
                        "help": parameter.help or "",
                        "required": bool(parameter.required),
                        "source": argument_source,
                        "value": not bool(parameter.is_flag),
                        "value_name": parameter.name.upper(),
                    }
                )
            else:
                arguments.append(
                    {
                        "name": parameter.name,
                        "required": bool(parameter.required),
                        "source": argument_source,
                    }
                )

        result.append(
            {
                "path": " ".join(current_path),
                "summary": _short_help(command),
                "source": source,
                "summary_source": summary_source,
                "arguments": arguments,
                "options": options,
            }
        )
    return result


def _reference_data() -> dict[str, Any]:
    root = typer.main.get_command(app)
    functions = _functions()
    app_definition = next(
        node
        for node in ast.walk(ast.parse(CLI_PATH.read_text(encoding="utf-8")))
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "app" for target in node.targets)
    )
    root_options: list[dict[str, Any]] = []
    callback = root.callback
    callback_function = functions[callback.__name__]
    for parameter in root.params:
        if parameter.__class__.__name__ != "TyperOption":
            continue
        root_options.append(
            {
                "flags": list(parameter.opts)
                + list(getattr(parameter, "secondary_opts", [])),
                "help": parameter.help or "",
                "source": _source_line(
                    callback_function,
                    parameter.name if parameter.name == "verbose" else None,
                )
                if parameter.name == "verbose"
                else f"{CLI_SOURCE}:{app_definition.lineno}",
            }
        )

    return {
        "source_file": CLI_SOURCE,
        "help_flag": {
            "flags": ["--help"],
            "help": "Show this message and exit.",
            "source": f"{CLI_SOURCE}:{app_definition.lineno}",
        },
        "root_options": root_options,
        "commands": _commands(root),
    }


def test_reference_json_matches_visible_cli_tree_and_source_locations() -> None:
    expected = _reference_data()
    saved = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert saved == expected



def test_static_page_renders_reference_data_without_client_javascript() -> None:
    page = PAGE_PATH.read_text(encoding="utf-8")
    assert "_commands.json" in page
    assert "command.path" in page
    assert "command.source" in page
    assert "option.source" in page
    assert "argument.source" in page
    assert "<script" not in page.lower()
    assert "client:" not in page
    # f3acc08 (Leo): the page became a real, indexed page with its props from
    # site_src/pages.yaml, replacing the WO-137 noindex placeholder
    assert 'pageProps("developers-cli")' in page
    assert "noindex" not in page
