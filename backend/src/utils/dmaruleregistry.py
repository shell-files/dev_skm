"""
dmaruleregistry.py
레이어: Utils
역할: DMA 규칙 레지스트리 — 규칙 카드 로딩·캐싱·버전 관리.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.utils.dmarulevalidator import (
    DmaRuleValidationError,
    EXPECTED_RULE_VERSION,
    EXPECTED_ARCHITECTURE_REVISION,
    EXPECTED_HASH_ALGORITHM,
    EXPECTED_POLICY_FILES,
    EXPECTED_CAPABILITY_KEYS,
    validatePath,
    validateManifest,
    validatePolicies,
    validatePolicyVersions,
    validateBundle,
    validateMediaEventResolverPolicy,
    validateKcgsScreeningPolicy,
    validateKisScreeningPolicy,
)

# backend/src/utils/dmaruleregistry.py -> parents[1] == backend/src
RUNTIME_CONFIG_DIR = Path(__file__).resolve().parents[1] / "resources" / "dma" / "v1_3_mvp"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class RuntimeConfigV13:
    """Immutable snapshot of the loaded v1.3 slim runtime config bundle."""
    ruleVersion: str
    architectureRevision: str
    configHash: str
    manifest: Dict[str, Any]
    policies: Dict[str, Dict[str, Any]]
    capabilities: Dict[str, str]


_lock = threading.RLock()
_cache: Optional[RuntimeConfigV13] = None


def readJson(path: Path) -> Any:
    if not path.exists():
        raise DmaRuleValidationError(f"Required runtime config file is missing: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        raise DmaRuleValidationError(f"Unable to read runtime config file {path.name}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DmaRuleValidationError(f"Invalid JSON in runtime config file {path.name}: {exc}") from exc


def _canonicalJson(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def computeConfigHash(policies: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for filename in sorted(policies):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(_canonicalJson(policies[filename]).encode("utf-8"))
        digest.update(b"\x00")
    return "sha256:" + digest.hexdigest()


def _resolveCapabilities(manifest: Dict[str, Any]) -> Dict[str, str]:
    capabilities = manifest["capabilities"]
    missingCaps = EXPECTED_CAPABILITY_KEYS - set(capabilities)
    if missingCaps:
        raise DmaRuleValidationError(f"manifest.capabilities missing required keys: {sorted(missingCaps)}")
    return copy.deepcopy({str(k): str(v) for k, v in capabilities.items()})


def _loadBundle() -> RuntimeConfigV13:
    manifest = readJson(RUNTIME_CONFIG_DIR / MANIFEST_FILENAME)
    if not isinstance(manifest, dict):
        raise DmaRuleValidationError("manifest.json must be a JSON object")
    validateManifest(manifest)
    policies: Dict[str, Dict[str, Any]] = {}
    for filename in manifest["runtimePolicyFiles"]:
        safeName = validatePath(filename)
        policies[safeName] = readJson(RUNTIME_CONFIG_DIR / safeName)
    validateBundle(manifest, policies)
    configHash = computeConfigHash(policies)
    capabilities = _resolveCapabilities(manifest)
    return RuntimeConfigV13(
        ruleVersion=manifest["ruleVersion"],
        architectureRevision=manifest["architectureRevision"],
        configHash=configHash,
        manifest=manifest,
        policies=policies,
        capabilities=capabilities,
    )


def getDmaRules(forceReload: bool = False) -> RuntimeConfigV13:
    global _cache
    with _lock:
        if _cache is None or forceReload:
            _cache = _loadBundle()
        return _cache


def resetDmaRulesForTest() -> None:
    global _cache
    with _lock:
        _cache = None


def getManifest() -> Dict[str, Any]:
    return copy.deepcopy(getDmaRules().manifest)


def getAllPolicies() -> Dict[str, Dict[str, Any]]:
    return copy.deepcopy(getDmaRules().policies)


def getPolicy(name: str) -> Dict[str, Any]:
    filename = name if name.endswith(".json") else f"{name}.json"
    filename = validatePath(filename)
    policies = getDmaRules().policies
    if filename not in policies:
        raise DmaRuleValidationError(f"Unknown runtime policy: {name!r}")
    return copy.deepcopy(policies[filename])


def getConfigHash() -> str:
    return getDmaRules().configHash


def getRuleVersion() -> str:
    return getDmaRules().ruleVersion


def getArchRevision() -> str:
    return getDmaRules().architectureRevision


def getCapabilities() -> Dict[str, str]:
    return copy.deepcopy(getDmaRules().capabilities)


def getCapability(name: str) -> Optional[str]:
    return getDmaRules().capabilities.get(name)


__all__ = [
    "RUNTIME_CONFIG_DIR",
    "MANIFEST_FILENAME",
    "EXPECTED_RULE_VERSION",
    "EXPECTED_ARCHITECTURE_REVISION",
    "EXPECTED_HASH_ALGORITHM",
    "EXPECTED_POLICY_FILES",
    "EXPECTED_CAPABILITY_KEYS",
    "DmaRuleValidationError",
    "RuntimeConfigV13",
    "validatePath",
    "validateManifest",
    "validatePolicies",
    "validatePolicyVersions",
    "validateBundle",
    "validateMediaEventResolverPolicy",
    "validateKcgsScreeningPolicy",
    "validateKisScreeningPolicy",
    "readJson",
    "computeConfigHash",
    "getDmaRules",
    "resetDmaRulesForTest",
    "getManifest",
    "getAllPolicies",
    "getPolicy",
    "getConfigHash",
    "getRuleVersion",
    "getArchRevision",
    "getCapabilities",
    "getCapability",
]
