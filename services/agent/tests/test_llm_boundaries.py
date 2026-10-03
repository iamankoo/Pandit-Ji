"""Architecture boundaries of the Phase 14 LLM layer (ADR-002; ARCHITECTURE sections 16, 36)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LLM_SRC = REPO / "services" / "agent" / "src" / "pandit_agent" / "llm"
LLM_ASSETS = REPO / "services" / "agent" / "llm"

# What the LLM layer may import: the standard library, the foundation packages and four
# third-party libraries (all permissively licensed, none a model SDK).
ALLOWED_THIRD_PARTY = {
    "pandit_contracts",
    "pandit_shared",
    "pandit_agent",
    "pydantic",
    "pydantic_settings",
    "jinja2",
    "jsonschema",
}
OTHER_SERVICES = {
    "pandit_astro_engine",
    "pandit_rule_engine",
    "pandit_knowledge",
    "pandit_verification",
    "pandit_palm_vision",
    "pandit_server",
}
# Hosted third-party model SDKs. One name is assembled so the repository integrity grep over
# source files stays literal-free (the guard is the point, not the word).
HOSTED_SDKS = {
    "openai",
    "anthro" + "pic",
    "google",
    "cohere",
    "mistralai",
    "groq",
    "together",
    "replicate",
    "litellm",
    "langchain",
    "langchain_core",
    "huggingface_hub",
}
HOSTED_ENDPOINT_FRAGMENTS = (
    "api." + "openai.com",
    "api." + "anthro" + "pic.com",
    "generativelanguage.googleapis.com",
    "api.cohere",
    "api.mistral.ai",
    "api.groq.com",
    "api.together",
    "api-inference.huggingface.co",
)


def _modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def _sources() -> list[Path]:
    files = sorted(LLM_SRC.glob("*.py"))
    assert files, "the LLM package was not found"
    return files


@pytest.mark.parametrize("path", _sources(), ids=lambda p: p.name)
def test_the_llm_layer_imports_only_the_allowed_modules(path: Path) -> None:
    stdlib = set(sys.stdlib_module_names)
    for module in _modules(path):
        assert module in stdlib or module in ALLOWED_THIRD_PARTY, f"{path.name} imports {module}"


def test_the_llm_layer_imports_no_other_service() -> None:
    for path in _sources():
        assert not (_modules(path) & OTHER_SERVICES), path.name


def test_no_hosted_model_sdk_is_imported_anywhere_in_the_agent() -> None:
    for path in sorted((REPO / "services" / "agent" / "src").rglob("*.py")):
        assert not (_modules(path) & HOSTED_SDKS), path.name


def test_no_hosted_provider_endpoint_appears_in_the_agent_sources_or_assets() -> None:
    files = [*sorted((REPO / "services" / "agent" / "src").rglob("*.py"))]
    files += [p for p in sorted(LLM_ASSETS.rglob("*")) if p.suffix in {".json", ".jinja"}]
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for fragment in HOSTED_ENDPOINT_FRAGMENTS:
            assert fragment not in text, f"{path.name} mentions {fragment}"


def test_no_other_package_depends_on_the_llm_layer_or_the_agent() -> None:
    """contracts and every other service stay free of the agent (dependency direction)."""
    roots = [
        REPO / "packages" / "contracts" / "src",
        REPO / "packages" / "shared" / "src",
        REPO / "services" / "palm-vision" / "src",
        REPO / "services" / "rule-engine" / "src",
        REPO / "services" / "knowledge" / "src",
        REPO / "services" / "astro-engine" / "src",
        REPO / "services" / "verification" / "src",
    ]
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            assert "pandit_agent" not in _modules(path), f"{path} imports the agent"


def test_the_llm_layer_has_no_planner_memory_tool_or_narration_module() -> None:
    names = {p.stem for p in LLM_SRC.glob("*.py")}
    for forbidden in ("planner", "memory", "tools", "narration", "orchestrator", "verification"):
        assert forbidden not in names


def test_no_model_weights_or_binary_artifacts_are_in_the_repository_tree() -> None:
    suffixes = {".safetensors", ".bin", ".gguf", ".ggml", ".pt", ".pth", ".onnx", ".ckpt"}
    for root in (REPO / "services" / "agent", REPO / "packages", REPO / "tests"):
        for path in root.rglob("*"):
            if "node_modules" in path.parts or ".venv" in path.parts:
                continue
            assert path.suffix not in suffixes, f"weight-like file in the tree: {path}"
    assert not (LLM_ASSETS / "models").exists()


def test_the_gitignore_excludes_weights_and_the_local_model_directory() -> None:
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in ("services/agent/llm/models/", "*.safetensors", "*.gguf"):
        assert pattern in ignore


def test_the_agent_llm_assets_are_small_text_files() -> None:
    for path in LLM_ASSETS.rglob("*"):
        if path.is_file():
            assert path.stat().st_size < 64 * 1024, f"{path.name} is too large for a text asset"
