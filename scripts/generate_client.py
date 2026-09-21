"""Генерация JavaScript-клиента из OpenAPI-контракта.

Клиент повторяет operationId из api/openapi.yaml, поэтому frontend и
backend используют одни и те же имена операций и путей.

Запуск:
    python scripts/generate_client.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "api" / "openapi.yaml"
OUTPUT = ROOT / "frontend" / "js" / "api-client.js"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _signature(path: str, operation: dict) -> tuple[str, str, bool]:
    path_params = re.findall(r"\{([^}]+)\}", path)
    query_params = [
        parameter["name"]
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query"
    ]
    has_body = "requestBody" in operation

    args: list[str] = list(path_params)
    if query_params:
        args.append("query = {}")
    if has_body:
        args.append("body")

    options: list[str] = []
    if query_params:
        options.append("query")
    if has_body:
        options.append("body")
    return ", ".join(args), ", ".join(options), has_body


def _url_expression(path: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in re.finditer(r"\{([^}]+)\}", path):
        parts.append(path[cursor : match.start()])
        parts.append("${encodeURIComponent(" + match.group(1) + ")}")
        cursor = match.end()
    parts.append(path[cursor:])
    if not any(part.startswith("${") for part in parts):
        return "'" + path + "'"
    return "`" + "".join(parts) + "`"


def generate() -> str:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    lines: list[str] = [
        "// AUTO-GENERATED FILE. DO NOT EDIT.",
        "// Source: api/openapi.yaml",
        "// Generator: scripts/generate_client.py",
        "",
        "export class ApiError extends Error {",
        "  constructor(status, detail, code) {",
        "    super(detail || 'Ошибка запроса');",
        "    this.name = 'ApiError';",
        "    this.status = status;",
        "    this.detail = detail || 'Ошибка запроса';",
        "    this.code = code || 'error';",
        "  }",
        "}",
        "",
        "export class ApiClient {",
        "  constructor(baseUrl = '') {",
        "    this.baseUrl = baseUrl;",
        "  }",
        "",
        "  async request(method, path, { query, body } = {}) {",
        "    const url = new URL(this.baseUrl + path, window.location.origin);",
        "    if (query) {",
        "      Object.entries(query).forEach(([key, value]) => {",
        "        if (value !== undefined && value !== null && value !== '') {",
        "          url.searchParams.set(key, value);",
        "        }",
        "      });",
        "    }",
        "    const options = {",
        "      method,",
        "      credentials: 'include',",
        "      headers: { Accept: 'application/json' },",
        "    };",
        "    if (body !== undefined) {",
        "      options.headers['Content-Type'] = 'application/json';",
        "      options.body = JSON.stringify(body);",
        "    }",
        "    const response = await fetch(url, options);",
        "    if (response.status === 204) {",
        "      return null;",
        "    }",
        "    const contentType = response.headers.get('content-type') || '';",
        "    const data = contentType.includes('application/json')",
        "      ? await response.json().catch(() => null)",
        "      : await response.text();",
        "    if (!response.ok) {",
        "      const detail = data && typeof data === 'object' ? data.detail : data;",
        "      const code = data && typeof data === 'object' ? data.code : undefined;",
        "      throw new ApiError(response.status, detail, code);",
        "    }",
        "    return data;",
        "  }",
        "",
    ]

    for path, item in spec.get("paths", {}).items():
        for method, operation in item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not operation_id:
                continue
            args, options, has_body = _signature(path, operation)
            summary = operation.get("summary", "")
            method_name = operation_id
            lines.append(f"  /** {summary} */")
            lines.append(f"  {method_name}({args}) {{")
            call_options = []
            if options:
                call_options.append("{ " + options + " }")
            lines.append(
                f"    return this.request('{method.upper()}', {_url_expression(path)}"
                + (f", {call_options[0]}" if call_options else "")
                + ");"
            )
            lines.append("  }")
            lines.append("")

    lines.append("}")
    lines.append("")
    lines.append("export const api = new ApiClient();")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generate(), encoding="utf-8")
    print(f"Клиент сгенерирован: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
