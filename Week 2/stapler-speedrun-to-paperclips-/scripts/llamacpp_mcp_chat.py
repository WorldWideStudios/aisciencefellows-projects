from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import anyio
import requests
from mcp import ClientSession, StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LLAMACPP_BASE_URL = os.environ.get("LLAMACPP_BASE_URL", "http://127.0.0.1:8080/v1")


def _build_tool_catalog(tools: list[Any]) -> str:
    lines: list[str] = []
    for tool in tools:
        description = (tool.description or "No description provided.").strip()
        schema = json.dumps(tool.inputSchema, indent=2, ensure_ascii=False)
        lines.append(f"- {tool.name}: {description}\n  inputSchema: {schema}")
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None


def _truncate(text: str, limit: int = 6000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _result_to_text(result: Any) -> str:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, indent=2, ensure_ascii=False)

    content_blocks = getattr(result, "content", []) or []
    parts: list[str] = []
    for block in content_blocks:
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            parts.append(block.text)
        else:
            try:
                parts.append(json.dumps(block.model_dump(), ensure_ascii=False))
            except Exception:
                parts.append(str(block))

    if parts:
        return "\n".join(parts)

    try:
        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    except Exception:
        return str(result)


def _build_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _chat_completion(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    api_key: str | None,
    temperature: float,
) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("llama.cpp returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _detect_model(base_url: str, api_key: str | None) -> str:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()

    models = payload.get("data") or []
    if not models:
        raise RuntimeError("Could not auto-detect a llama.cpp model id; pass --model explicitly")

    first = models[0]
    model_id = first.get("id")
    if not model_id:
        raise RuntimeError("llama.cpp /v1/models response did not include a model id")
    return model_id


async def _run_bridge(args: argparse.Namespace) -> int:
    model = args.model or _detect_model(args.llama_base_url, args.llama_api_key)

    server_parameters = StdioServerParameters(
        command=args.server_command,
        args=args.server_args,
        cwd=str(ROOT),
    )

    async with stdio_client(server_parameters) as streams:
        read_stream, write_stream = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_catalog = _build_tool_catalog(tools_result.tools)
            system_prompt = (
                "You are a bioscience assistant with access to MCP tools.\n\n"
                "When you need to use a tool, reply with a single JSON object in this exact form:\n"
                '{"type":"tool_call","tool_name":"name","arguments":{...}}\n\n'
                "When you are done, reply with a single JSON object in this exact form:\n"
                '{"type":"final","content":"your answer"}\n\n'
                "Do not use markdown fences. Do not add extra commentary outside the JSON object.\n\n"
                "Available tools:\n"
                f"{tool_catalog}"
            )
            messages = _build_messages(system_prompt, args.prompt)

            for step in range(args.max_steps):
                raw_reply = _chat_completion(
                    base_url=args.llama_base_url,
                    model=model,
                    messages=messages,
                    api_key=args.llama_api_key,
                    temperature=args.temperature,
                )

                parsed = _extract_json_object(raw_reply)
                if parsed is None:
                    print(raw_reply)
                    return 0

                reply_type = parsed.get("type")
                if reply_type == "final":
                    final_content = parsed.get("content", "")
                    print(final_content)
                    return 0

                if reply_type != "tool_call":
                    raise RuntimeError(f"Unexpected response from llama.cpp: {raw_reply}")

                tool_name = parsed.get("tool_name")
                arguments = parsed.get("arguments") or {}
                if not isinstance(tool_name, str) or not tool_name:
                    raise RuntimeError(f"Tool call is missing a valid tool_name: {raw_reply}")
                if not isinstance(arguments, dict):
                    raise RuntimeError(f"Tool call arguments must be a JSON object: {raw_reply}")

                tool_result = await session.call_tool(tool_name, arguments)
                tool_text = _truncate(_result_to_text(tool_result))

                messages.append({"role": "assistant", "content": raw_reply})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool result for {tool_name}:\n{tool_text}",
                    }
                )

            raise RuntimeError(f"Reached the maximum number of steps ({args.max_steps}) without a final answer")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask a local llama.cpp server to use this repository's MCP tools"
    )
    parser.add_argument("--prompt", required=True, help="User question to send to llama.cpp")
    parser.add_argument(
        "--llama-base-url",
        default=DEFAULT_LLAMACPP_BASE_URL,
        help="Base URL for the llama.cpp OpenAI-compatible API",
    )
    parser.add_argument(
        "--llama-api-key",
        default=os.environ.get("LLAMACPP_API_KEY"),
        help="Optional API key for llama.cpp if auth is enabled",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLAMACPP_MODEL"),
        help="Override the llama.cpp model id; otherwise auto-detect the first available model",
    )
    parser.add_argument(
        "--server-command",
        default=sys.executable,
        help="Command used to launch the MCP server process",
    )
    parser.add_argument(
        "--server-args",
        nargs="*",
        default=[str(ROOT / "server.py")],
        help="Arguments passed to the MCP server command",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Maximum tool-calling rounds before failing",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for llama.cpp",
    )
    args = parser.parse_args()

    try:
        return anyio.run(_run_bridge, args)
    except requests.RequestException as exc:
        print(f"llama.cpp request failed: {exc}", file=sys.stderr)
        return 1
    except ExceptionGroup as exc:
        if len(exc.exceptions) == 1 and isinstance(exc.exceptions[0], requests.RequestException):
            print(f"llama.cpp request failed: {exc.exceptions[0]}", file=sys.stderr)
            return 1
        print(f"Bridge failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Bridge failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())