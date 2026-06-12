"""
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/rule-registry
Responsibility: STEP 0 — Rule Load, Validate, Hash, Cache
- Own ALL runtime IO for the v1.3 MVP slim runtime config
- Inline all config validation (path guard, manifest, exact-set, rule-version)
- Compute canonical-JSON SHA-256 config hash over the 5 policy files only
- Provide a singleton cache, deep-copy reads, and a test cache reset
- Expose capability status
Public surface:
- RUNTIME_CONFIG_DIR, MANIFEST_FILENAME
- EXPECTED_RULE_VERSION, EXPECTED_ARCHITECTURE_REVISION, EXPECTED_POLICY_FILES
- DmaRuleValidationError
- RuntimeConfigV13
- validatePath
- getDmaRules / resetDmaRulesForTest / computeConfigHash
- getManifest / getAllPolicies / getPolicy
- getConfigHash / getRuleVersion / getArchRevision
- getCapabilities / getCapability
Do not:
- do not let services import or read these JSON files directly (Registry only)
- do not read docs/dma/** at runtime
- do not eval / exec config strings
- do not include the manifest in the config hash
- do not connect to a DB / Redis / Kafka
- do not enable hot reload
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

# =========================================================
# STEP 0. RULE LOAD / VALIDATE / HASH
# =========================================================

# SSOT contract constants
EXPECTED_RULE_VERSION = "dma-rule-v1.3-mvp"
EXPECTED_ARCHITECTURE_REVISION = "R4.1-SLIM"
EXPECTED_HASH_ALGORITHM = "SHA-256"

# Exact runtime policy file set. Manifest is excluded from this set and from the hash.
EXPECTED_POLICY_FILES = frozenset({
    "canonical_scoring_policy.json",
    "screening_policy.json",
    "survey_policy.json",
    "ai_fact_validation_policy.json",
    "selection_policy.json",
    "media_event_resolver_policy.json",
})

EXPECTED_CAPABILITY_KEYS = frozenset({
    "canonicalScoring",
    "benchmarkScreening",
    "surveyAggregation",
    "regulationBaseScreening",
    "regulationAutoClassification",
    "kcgsPillarSignal",
    "kcgsPillarBoostPropagation",
    "kisFinancialResilience",
    "mediaEventCanonicalAdapter",
})

_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_]+\.json$")

# backend/src/utils/dmaruleregistry.py -> parents[1] == backend/src
RUNTIME_CONFIG_DIR = Path(__file__).resolve().parents[1] / "resources" / "dma" / "v1_3_mvp"
MANIFEST_FILENAME = "manifest.json"

class DmaRuleValidationError(ValueError):
    """Raised when a v1.3 slim runtime config violates the contract."""


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


# STEP 0. Path guard — rejects traversal, absolute, nested, non-json filenames.
# Input: raw filename string from manifest.
# Output: validated safe filename string.
def validatePath(filename: Any) -> str:
    if not isinstance(filename, str):
        raise DmaRuleValidationError(f"Config filename must be a string, got {type(filename)!r}")
    raw = filename.strip()
    if not raw:
        raise DmaRuleValidationError("Config filename must not be empty")
    if ".." in raw:
        raise DmaRuleValidationError(f"Path traversal not allowed: {filename!r}")
    if raw.startswith("./") or raw.startswith(".\\"):
        raise DmaRuleValidationError(f"Relative './' prefix not allowed: {filename!r}")
    if "/" in raw or "\\" in raw:
        raise DmaRuleValidationError(f"Nested sub-paths not allowed: {filename!r}")
    if re.match(r"^[A-Za-z]:", raw):
        raise DmaRuleValidationError(f"Absolute paths not allowed: {filename!r}")
    if not raw.lower().endswith(".json"):
        raise DmaRuleValidationError(f"Only .json files allowed: {filename!r}")
    if not _SAFE_FILENAME_RE.match(raw):
        raise DmaRuleValidationError(f"Unsafe config filename: {filename!r}")
    return raw


def validateManifest(manifest: Dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise DmaRuleValidationError("manifest.json must be a JSON object")
    rv = manifest.get("ruleVersion")
    if rv != EXPECTED_RULE_VERSION:
        raise DmaRuleValidationError(
            f"manifest ruleVersion mismatch: expected {EXPECTED_RULE_VERSION!r}, got {rv!r}"
        )
    arch = manifest.get("architectureRevision")
    if arch != EXPECTED_ARCHITECTURE_REVISION:
        raise DmaRuleValidationError(
            f"manifest architectureRevision mismatch: expected {EXPECTED_ARCHITECTURE_REVISION!r}, got {arch!r}"
        )
    algo = manifest.get("hashAlgorithm")
    if algo != EXPECTED_HASH_ALGORITHM:
        raise DmaRuleValidationError(
            f"manifest hashAlgorithm mismatch: expected {EXPECTED_HASH_ALGORITHM!r}, got {algo!r}"
        )
    files = manifest.get("runtimePolicyFiles")
    if not isinstance(files, list) or not files:
        raise DmaRuleValidationError("manifest.runtimePolicyFiles must be a non-empty list")
    for name in files:
        validatePath(name)
    if len(set(files)) != len(files):
        raise DmaRuleValidationError("manifest.runtimePolicyFiles contains duplicates")
    validatePolicies(files)
    if manifest.get("serviceDirectJsonLoadAllowedYn") is not False:
        raise DmaRuleValidationError("manifest.serviceDirectJsonLoadAllowedYn must be false")
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        raise DmaRuleValidationError("manifest.capabilities must be a JSON object")
    missingCaps = EXPECTED_CAPABILITY_KEYS - set(capabilities)
    if missingCaps:
        raise DmaRuleValidationError(f"manifest.capabilities missing required keys: {sorted(missingCaps)}")


def validatePolicies(filenames: Iterable[str]) -> None:
    actual = set(filenames)
    missing = EXPECTED_POLICY_FILES - actual
    extra = actual - EXPECTED_POLICY_FILES
    if missing or extra:
        raise DmaRuleValidationError(
            f"runtime policy file set mismatch. missing={sorted(missing)} unexpected={sorted(extra)}"
        )


def validatePolicyVersions(policies: Dict[str, Dict[str, Any]]) -> None:
    for name, body in policies.items():
        if not isinstance(body, dict):
            raise DmaRuleValidationError(f"policy {name!r} must be a JSON object")
        version = body.get("ruleVersion")
        if version != EXPECTED_RULE_VERSION:
            raise DmaRuleValidationError(
                f"policy {name!r} ruleVersion mismatch: expected {EXPECTED_RULE_VERSION!r}, got {version!r}"
            )


def validateBundle(manifest: Dict[str, Any], policies: Dict[str, Dict[str, Any]]) -> None:
    validateManifest(manifest)
    validatePolicies(policies.keys())
    validatePolicyVersions(policies)


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
    """Canonical JSON: keys sorted, compact separators — hash-invariant to key order and whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# STEP 0. Compute SHA-256 hash over the 5 policy files (manifest excluded).
# Input: policy dict keyed by filename.
# Output: 'sha256:<hexdigest>' string.
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


# STEP 0. Load and cache the v1.3 slim runtime config bundle (singleton).
# Input: forceReload=True bypasses cache (used by tests).
# Output: immutable RuntimeConfigV13 snapshot.
def getDmaRules(forceReload: bool = False) -> RuntimeConfigV13:
    global _cache
    with _lock:
        if _cache is None or forceReload:
            _cache = _loadBundle()
        return _cache


def resetDmaRulesForTest() -> None:
    """Clear the singleton cache (test helper)."""
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
