from __future__ import annotations

from pathlib import Path

import yaml
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "api" / "openapi.yaml"
CLIENT_PATH = ROOT / "frontend" / "js" / "api-client.js"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def test_openapi_yaml_is_valid():
    spec = load_spec()
    validate(spec)
    assert spec["openapi"].startswith("3.0")
    assert spec["info"]["version"] == "0.1.0"


def test_every_contract_path_is_implemented():
    from backend.app.main import app

    spec = load_spec()
    generated = app.openapi()
    for path, operations in spec["paths"].items():
        assert path in generated["paths"], f"Путь не реализован: {path}"
        for method in operations:
            if method in HTTP_METHODS:
                assert method in generated["paths"][path], f"Метод не реализован: {method} {path}"


def test_operation_ids_are_unique_and_used_by_client():
    spec = load_spec()
    operation_ids: list[str] = []
    for operations in spec["paths"].values():
        for method, operation in operations.items():
            if method in HTTP_METHODS:
                operation_ids.append(operation["operationId"])
    assert len(operation_ids) == len(set(operation_ids))

    client = CLIENT_PATH.read_text(encoding="utf-8")
    for operation_id in operation_ids:
        assert f"  {operation_id}(" in client, f"Метод отсутствует в клиенте: {operation_id}"


def test_contract_has_expected_models():
    spec = load_spec()
    schemas = spec["components"]["schemas"]
    for name in ["User", "Student", "Group", "Teacher", "Subject", "DashboardStats", "Error"]:
        assert name in schemas

    from backend.app.contract import models

    for name in ["User", "Student", "Group", "Teacher", "Subject", "DashboardStats"]:
        assert hasattr(models, name)
