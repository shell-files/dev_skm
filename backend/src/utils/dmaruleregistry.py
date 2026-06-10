"""
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/config-registry
Responsibility:
- Own ALL runtime IO for the v1.3 MVP slim runtime config
- Load manifest + 5 policy files from backend/src/resources/dma/v1_3_mvp/
- Validate via dmarulevalidator (fail-fast)
- Compute a canonical-JSON SHA-256 config hash over the 5 policy files only
- Provide a singleton cache, deep-copy reads, and a test cache reset
- Expose Optional Capability status
Public surface:
- RUNTIME_CONFIG_DIR
- RuntimeConfigV13
- compute_config_hash
- load_runtime_config
- get_manifest / get_policy / get_all_policies
- get_config_hash / get_rule_version / get_architecture_revision
- get_capabilities / get_capability
- reset_cache
Do not:
- do not let services import or read these JSON files directly (Registry only)
- do not read docs/dma/** at runtime
- do not eval / exec config strings
- do not include the manifest, golden tests, or impl docs in the config hash
- do not connect to a DB / Redis / Kafka
- do not enable hot reload

Runtime은 이 Registry를 통해서만 Slim Config를 읽는다.
Hash 대상은 정책 5종이며 Manifest 자기 자신은 제외한다.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.utils import dmarulevalidator as validator
from src.utils.dmarulevalidator import DmaRuleValidationError

# backend/src/utils/dmaruleregistry.py -> parents[1] == backend/src
RUNTIME_CONFIG_DIR = Path(__file__).resolve().parents[1] / "resources" / "dma" / "v1_3_mvp"
MANIFEST_FILENAME = "manifest.json"

# Minimum / baseline capability contract (Phase A). Policy-declared capability
# overrides are merged on top of these defaults.
_DEFAULT_CAPABILITIES: Dict[str, str] = {
    "canonicalScoring": "READY",
    "benchmarkScreening": "READY",
    "surveyAggregation": "READY",
    "regulationBaseScreening": "READY",
    "regulationAutoClassification": "CONFIG_PENDING",
    "kcgsPillarSignal": "READY",
    "kcgsPillarBoostPropagation": "DATA_EXPORT_REQUIRED",
    "kisFinancialResilience": "DATA_EXPORT_REQUIRED",
    "mediaEventCanonicalAdapter": "CONFIG_PENDING",
}


@dataclass(frozen=True)
class RuntimeConfigV13:
    """Immutable snapshot of the loaded v1.3 slim runtime config bundle."""

    rule_version: str
    architecture_revision: str
    config_hash: str
    manifest: Dict[str, Any]
    policies: Dict[str, Dict[str, Any]]
    capabilities: Dict[str, str]


_lock = threading.RLock()
_cache: Optional[RuntimeConfigV13] = None


# ──────────────────────────────────────────────
# Config Hash
# ──────────────────────────────────────────────

def _canonical_json(obj: Any) -> str:
    """
    Canonical JSON form: keys sorted, no insignificant whitespace.
    This makes the hash invariant to key ordering and whitespace, while
    remaining sensitive to any value change.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_config_hash(policies: Mapping[str, Any]) -> str:
    """
    Compute the runtime config hash over the policy file set.

    - Canonical-JSON per file (sort_keys + compact separators)
    - Files folded in sorted filename order (deterministic)
    - A single NUL byte delimiter is placed between the filename and its
      canonical JSON, and after the JSON, so a value cannot "bleed" across files
    - Returns ``sha256:<hexdigest>``

    The manifest is intentionally NOT a hash input.
    """
    digest = hashlib.sha256()
    for filename in sorted(policies):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(_canonical_json(policies[filename]).encode("utf-8"))
        digest.update(b"\x00")
    return "sha256:" + digest.hexdigest()


# ──────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────

def _read_json(path: Path) -> Any:
    if not path.exists():
        raise DmaRuleValidationError(f"Required runtime config file is missing: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem error
        raise DmaRuleValidationError(f"Unable to read runtime config file {path.name}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DmaRuleValidationError(f"Invalid JSON in runtime config file {path.name}: {exc}") from exc


def _resolve_capabilities(manifest: Dict[str, Any], policies: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    capabilities = dict(_DEFAULT_CAPABILITIES)
    # Manifest-level declaration (full map) takes precedence over defaults.
    manifest_caps = manifest.get("capabilities")
    if isinstance(manifest_caps, dict):
        capabilities.update({str(k): str(v) for k, v in manifest_caps.items()})
    # Screening policy may restate the screening-specific subset.
    screening_caps = policies.get("screening_policy.json", {}).get("capabilities")
    if isinstance(screening_caps, dict):
        capabilities.update({str(k): str(v) for k, v in screening_caps.items()})
    return capabilities


def _load_bundle() -> RuntimeConfigV13:
    manifest = _read_json(RUNTIME_CONFIG_DIR / MANIFEST_FILENAME)
    if not isinstance(manifest, dict):
        raise DmaRuleValidationError("manifest.json must be a JSON object")

    # Validate manifest first so we trust its declared file list.
    validator.validate_manifest(manifest)

    policies: Dict[str, Dict[str, Any]] = {}
    for filename in manifest["runtimePolicyFiles"]:
        safe_name = validator.validate_config_filename(filename)
        policies[safe_name] = _read_json(RUNTIME_CONFIG_DIR / safe_name)

    # Full bundle validation (exact set + per-policy ruleVersion).
    validator.validate_runtime_bundle(manifest, policies)

    config_hash = compute_config_hash(policies)
    capabilities = _resolve_capabilities(manifest, policies)

    return RuntimeConfigV13(
        rule_version=manifest["ruleVersion"],
        architecture_revision=manifest["architectureRevision"],
        config_hash=config_hash,
        manifest=manifest,
        policies=policies,
        capabilities=capabilities,
    )


def load_runtime_config(force_reload: bool = False) -> RuntimeConfigV13:
    """
    Load (and cache) the v1.3 slim runtime config bundle.

    Singleton cached; pass ``force_reload=True`` or call :func:`reset_cache`
    to reload (used by tests). Fail-fast: any missing file, invalid JSON, or
    contract violation raises DmaRuleValidationError.
    """
    global _cache
    with _lock:
        if _cache is None or force_reload:
            _cache = _load_bundle()
        return _cache


def reset_cache() -> None:
    """Clear the singleton cache (test helper)."""
    global _cache
    with _lock:
        _cache = None


# ──────────────────────────────────────────────
# Read accessors (deep-copy returns; callers cannot mutate cached state)
# ──────────────────────────────────────────────

def get_manifest() -> Dict[str, Any]:
    return copy.deepcopy(load_runtime_config().manifest)


def get_all_policies() -> Dict[str, Dict[str, Any]]:
    return copy.deepcopy(load_runtime_config().policies)


def get_policy(name: str) -> Dict[str, Any]:
    """
    Return a deep copy of one policy by filename (e.g. ``screening_policy.json``)
    or by bare stem (``screening_policy``).
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    filename = validator.validate_config_filename(filename)
    policies = load_runtime_config().policies
    if filename not in policies:
        raise DmaRuleValidationError(f"Unknown runtime policy: {name!r}")
    return copy.deepcopy(policies[filename])


def get_config_hash() -> str:
    return load_runtime_config().config_hash


def get_rule_version() -> str:
    return load_runtime_config().rule_version


def get_architecture_revision() -> str:
    return load_runtime_config().architecture_revision


def get_capabilities() -> Dict[str, str]:
    return copy.deepcopy(load_runtime_config().capabilities)


def get_capability(name: str) -> Optional[str]:
    return load_runtime_config().capabilities.get(name)


__all__ = [
    "RUNTIME_CONFIG_DIR",
    "MANIFEST_FILENAME",
    "RuntimeConfigV13",
    "compute_config_hash",
    "load_runtime_config",
    "reset_cache",
    "get_manifest",
    "get_all_policies",
    "get_policy",
    "get_config_hash",
    "get_rule_version",
    "get_architecture_revision",
    "get_capabilities",
    "get_capability",
]
