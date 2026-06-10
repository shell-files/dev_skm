"""
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/config-validation
Responsibility:
- Validate the DMA v1.3 MVP runtime slim config manifest and 5 policy files
- Guard runtime config file paths against traversal / absolute / nested / non-json paths
- Assert manifest version / ruleVersion / architectureRevision contracts
- Assert the runtime policy file set is an exact match (no more, no less)
- Assert each policy file declares the expected ruleVersion
Public surface:
- DmaRuleValidationError
- EXPECTED_RULE_VERSION
- EXPECTED_ARCHITECTURE_REVISION
- EXPECTED_POLICY_FILES
- validate_config_filename
- validate_manifest
- validate_policy_file_set
- validate_policy_rule_versions
- validate_runtime_bundle
Do not:
- do not read or load files here (the registry owns IO); this module is pure validation
- do not connect to a DB
- do not eval / exec config strings
- do not mutate inputs

이 모듈은 v1.3 MVP Slim Runtime Config(Manifest 1종 + Policy 5종)에 대한
순수 검증(Validation) 로직만 담는다. 파일 IO와 Hash 계산은 dmaruleregistry가 담당한다.
충돌 시 우선순위: Master Prompt → 00_LIVE_DB_BASELINE_ADDENDUM → 01_EXECUTE_PHASE_A → plans → references.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

# ──────────────────────────────────────────────
# Contract constants (v1.3 MVP / R4.1-SLIM)
# ──────────────────────────────────────────────

EXPECTED_RULE_VERSION = "dma-rule-v1.3-mvp"
EXPECTED_ARCHITECTURE_REVISION = "R4.1-SLIM"
EXPECTED_HASH_ALGORITHM = "SHA-256"

# Exact runtime policy file set. Manifest itself is NOT a policy file and is NOT
# part of this set (and is excluded from the config hash).
EXPECTED_POLICY_FILES = frozenset(
    {
        "canonical_scoring_policy.json",
        "screening_policy.json",
        "survey_policy.json",
        "ai_fact_validation_policy.json",
        "selection_policy.json",
    }
)

# A safe runtime config filename: a bare "<name>.json" token, no directory parts.
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_]+\.json$")


class DmaRuleValidationError(ValueError):
    """Raised when a v1.3 slim runtime config violates the contract."""


# ──────────────────────────────────────────────
# Path guard
# ──────────────────────────────────────────────

def validate_config_filename(filename: Any) -> str:
    """
    Reject anything that is not a bare ``<name>.json`` file token.

    Rejected:
    - non-string input
    - empty / whitespace
    - parent traversal ``..``
    - explicit current dir ``./``
    - absolute paths (POSIX ``/`` or Windows drive ``C:\\``)
    - nested sub paths (contains ``/`` or ``\\``)
    - non ``.json`` extensions
    """
    if not isinstance(filename, str):
        raise DmaRuleValidationError(f"Config filename must be a string, got {type(filename)!r}")

    raw = filename.strip()
    if not raw:
        raise DmaRuleValidationError("Config filename must not be empty")

    if ".." in raw:
        raise DmaRuleValidationError(f"Path traversal is not allowed in config filename: {filename!r}")
    if raw.startswith("./") or raw.startswith(".\\"):
        raise DmaRuleValidationError(f"Relative './' prefix is not allowed in config filename: {filename!r}")
    if "/" in raw or "\\" in raw:
        raise DmaRuleValidationError(f"Nested sub-paths are not allowed in config filename: {filename!r}")
    # Absolute Windows drive path like 'C:foo.json'
    if re.match(r"^[A-Za-z]:", raw):
        raise DmaRuleValidationError(f"Absolute paths are not allowed in config filename: {filename!r}")
    if not raw.lower().endswith(".json"):
        raise DmaRuleValidationError(f"Only .json runtime config files are allowed: {filename!r}")
    if not _SAFE_FILENAME_RE.match(raw):
        raise DmaRuleValidationError(f"Unsafe config filename: {filename!r}")
    return raw


# ──────────────────────────────────────────────
# Manifest / policy-set / version validation
# ──────────────────────────────────────────────

def validate_manifest(manifest: Dict[str, Any]) -> None:
    """Validate the manifest contract. Raises DmaRuleValidationError on any violation."""
    if not isinstance(manifest, dict):
        raise DmaRuleValidationError("manifest.json must be a JSON object")

    rule_version = manifest.get("ruleVersion")
    if rule_version != EXPECTED_RULE_VERSION:
        raise DmaRuleValidationError(
            f"manifest ruleVersion mismatch: expected {EXPECTED_RULE_VERSION!r}, got {rule_version!r}"
        )

    architecture = manifest.get("architectureRevision")
    if architecture != EXPECTED_ARCHITECTURE_REVISION:
        raise DmaRuleValidationError(
            f"manifest architectureRevision mismatch: expected {EXPECTED_ARCHITECTURE_REVISION!r}, "
            f"got {architecture!r}"
        )

    hash_algorithm = manifest.get("hashAlgorithm")
    if hash_algorithm != EXPECTED_HASH_ALGORITHM:
        raise DmaRuleValidationError(
            f"manifest hashAlgorithm mismatch: expected {EXPECTED_HASH_ALGORITHM!r}, got {hash_algorithm!r}"
        )

    files = manifest.get("runtimePolicyFiles")
    if not isinstance(files, list) or not files:
        raise DmaRuleValidationError("manifest.runtimePolicyFiles must be a non-empty list")

    for name in files:
        validate_config_filename(name)

    if len(set(files)) != len(files):
        raise DmaRuleValidationError("manifest.runtimePolicyFiles contains duplicates")

    validate_policy_file_set(files)

    # Runtime must not allow services to load JSON directly or hot reload.
    if manifest.get("serviceDirectJsonLoadAllowedYn") is not False:
        raise DmaRuleValidationError("manifest.serviceDirectJsonLoadAllowedYn must be false")


def validate_policy_file_set(filenames: Iterable[str]) -> None:
    """Assert that the declared policy file set is exactly EXPECTED_POLICY_FILES."""
    actual = set(filenames)
    missing = EXPECTED_POLICY_FILES - actual
    extra = actual - EXPECTED_POLICY_FILES
    if missing or extra:
        raise DmaRuleValidationError(
            "runtime policy file set mismatch. "
            f"missing={sorted(missing)} unexpected={sorted(extra)}"
        )


def validate_policy_rule_versions(policies: Dict[str, Dict[str, Any]]) -> None:
    """Assert each loaded policy declares the expected ruleVersion."""
    for name, body in policies.items():
        if not isinstance(body, dict):
            raise DmaRuleValidationError(f"policy {name!r} must be a JSON object")
        version = body.get("ruleVersion")
        if version != EXPECTED_RULE_VERSION:
            raise DmaRuleValidationError(
                f"policy {name!r} ruleVersion mismatch: expected {EXPECTED_RULE_VERSION!r}, got {version!r}"
            )


def validate_runtime_bundle(manifest: Dict[str, Any], policies: Dict[str, Dict[str, Any]]) -> None:
    """
    Validate the full runtime bundle: manifest contract, exact policy set,
    and per-policy ruleVersion. Raises DmaRuleValidationError on any violation.
    """
    validate_manifest(manifest)
    validate_policy_file_set(policies.keys())
    validate_policy_rule_versions(policies)


__all__ = [
    "DmaRuleValidationError",
    "EXPECTED_RULE_VERSION",
    "EXPECTED_ARCHITECTURE_REVISION",
    "EXPECTED_HASH_ALGORITHM",
    "EXPECTED_POLICY_FILES",
    "validate_config_filename",
    "validate_manifest",
    "validate_policy_file_set",
    "validate_policy_rule_versions",
    "validate_runtime_bundle",
]
