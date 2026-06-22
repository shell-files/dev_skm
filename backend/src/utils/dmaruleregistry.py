"""
<<<<<<< HEAD
dmaruleregistry.py
레이어: Utils
역할: DMA 규칙 레지스트리 — 규칙 카드 로딩·캐싱·버전 관리.
"""
=======
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/rule-registry
Responsibility: STEP 0 — Rule Load, Validate, Hash, Cache
- Own ALL runtime IO for the v1.3 MVP slim runtime config
- Inline all config validation (path guard, manifest, exact-set, rule-version)
- Compute canonical-JSON SHA-256 config hash over the 6 policy files only
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

>>>>>>> origin/skm_test
from __future__ import annotations

import copy
import hashlib
import json
<<<<<<< HEAD
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
=======
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

# Exact runtime policy file set (6 files). Manifest is excluded from this set and from the hash.
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
>>>>>>> origin/skm_test

# backend/src/utils/dmaruleregistry.py -> parents[1] == backend/src
RUNTIME_CONFIG_DIR = Path(__file__).resolve().parents[1] / "resources" / "dma" / "v1_3_mvp"
MANIFEST_FILENAME = "manifest.json"

<<<<<<< HEAD
=======
class DmaRuleValidationError(ValueError):
    """Raised when a v1.3 slim runtime config violates the contract."""

>>>>>>> origin/skm_test

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


<<<<<<< HEAD
def readJson(path: Path) -> Any:
    """지정 경로의 JSON 파일을 읽어 파싱한다. 파일 미존재 또는 JSON 오류 시 DmaRuleValidationError를 발생시킨다."""
=======
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


_KNOWN_DEDUP_MANDATORY_KEYS = frozenset({"subIssueCode", "normalizedEventType", "eventDateBucket"})
_KCGS_GRADE_ORDER_BEST_TO_WORST = ["S", "A+", "A", "B+", "B", "C", "D"]
_KCGS_PILLARS = ["E", "S", "G"]
_KCGS_TREND_MODIFIER_KEYS = frozenset({
    "downgradeTwoOrMore",
    "downgradeOne",
    "flat",
    "upgrade",
    "insufficientData",
})


def _validateBandSection(section: Mapping[str, Any], section_name: str, must_have_bands: bool) -> None:
    if "missingPolicy" not in section:
        raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name} missing 'missingPolicy'")
    if not must_have_bands:
        return
    bands = section.get("bands")
    if not isinstance(bands, list) or not bands:
        raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands must be a non-empty list")
    for idx, band in enumerate(bands):
        if not isinstance(band, dict):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] must be a dict")
        if "score" not in band:
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] missing 'score'")
        score = band["score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 5):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] score must be in 0..5")
        if "minInclusive" not in band:
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] missing 'minInclusive'")
        if not isinstance(band["minInclusive"], bool):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] minInclusive must be bool")
        if "maxExclusive" not in band:
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] missing 'maxExclusive'")
        if not isinstance(band["maxExclusive"], bool):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] maxExclusive must be bool")
        lo = band.get("min")
        hi = band.get("max")
        if lo is not None and not isinstance(lo, (int, float)):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] min must be numeric or null")
        if hi is not None and not isinstance(hi, (int, float)):
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] max must be numeric or null")
        if lo is not None and hi is not None and lo > hi:
            raise DmaRuleValidationError(f"media_event_resolver_policy: {section_name}.bands[{idx}] min > max (reversed order)")
    # Contiguity / overlap between consecutive bands
    for idx in range(len(bands) - 1):
        hi = bands[idx].get("max")
        lo_next = bands[idx + 1].get("min")
        if hi is not None and lo_next is not None:
            if hi < lo_next:
                raise DmaRuleValidationError(
                    f"media_event_resolver_policy: {section_name}.bands[{idx}]->[{idx+1}] gap (max={hi} < min={lo_next})"
                )
            if hi > lo_next:
                raise DmaRuleValidationError(
                    f"media_event_resolver_policy: {section_name}.bands[{idx}]->[{idx+1}] overlap (max={hi} > min={lo_next})"
                )
            # hi == lo_next: verify exactly one endpoint includes the boundary
            if hi == lo_next:
                prev_max_exc = bool(bands[idx].get("maxExclusive", False))
                next_min_inc = bool(bands[idx + 1].get("minInclusive", True))
                if not prev_max_exc and next_min_inc:
                    raise DmaRuleValidationError(
                        f"media_event_resolver_policy: {section_name}.bands[{idx}]->[{idx+1}] boundary duplicate: both include {hi}"
                    )
                if prev_max_exc and not next_min_inc:
                    raise DmaRuleValidationError(
                        f"media_event_resolver_policy: {section_name}.bands[{idx}]->[{idx+1}] boundary gap: neither includes {hi}"
                    )


def validateMediaEventResolverPolicy(policy: Mapping[str, Any]) -> None:
    """Fail-fast structural validation for media_event_resolver_policy.json."""
    if not isinstance(policy, Mapping):
        raise DmaRuleValidationError("media_event_resolver_policy must be a JSON object")
    for key in (
        "version", "ruleVersion", "resolverVersion", "scoreDecisionByAiAllowedYn",
        "eventTypeNormalization", "impactScaleRules", "impactScopeRules",
        "impactLikelihoodRules", "impactIrremediabilityRules",
        "financialMagnitudeRules", "financialLikelihoodRules",
        "timeHorizonRules", "eventDedupRules", "ratioValueContract", "missingPolicy",
    ):
        if key not in policy:
            raise DmaRuleValidationError(f"media_event_resolver_policy missing required key: '{key}'")

    if policy["scoreDecisionByAiAllowedYn"] is not False:
        raise DmaRuleValidationError("media_event_resolver_policy: scoreDecisionByAiAllowedYn must be false")

    etn = policy["eventTypeNormalization"]
    for k in ("unknownPolicy", "aliases"):
        if k not in etn:
            raise DmaRuleValidationError(f"media_event_resolver_policy: eventTypeNormalization missing '{k}'")

    _validateBandSection(policy["impactScaleRules"], "impactScaleRules", must_have_bands=True)

    scope = policy["impactScopeRules"]
    if "enabledYn" not in scope:
        raise DmaRuleValidationError("media_event_resolver_policy: impactScopeRules missing 'enabledYn'")
    if scope["enabledYn"] is True:
        if not scope.get("sourceField"):
            raise DmaRuleValidationError("media_event_resolver_policy: impactScopeRules enabledYn=true requires sourceField")
        _validateBandSection(scope, "impactScopeRules", must_have_bands=True)
    else:
        if "missingPolicy" not in scope:
            raise DmaRuleValidationError("media_event_resolver_policy: impactScopeRules missing 'missingPolicy'")

    _validateBandSection(policy["impactLikelihoodRules"], "impactLikelihoodRules", must_have_bands=True)

    irrem = policy["impactIrremediabilityRules"]
    if "missingPolicy" not in irrem:
        raise DmaRuleValidationError("media_event_resolver_policy: impactIrremediabilityRules missing 'missingPolicy'")

    mag = policy["financialMagnitudeRules"]
    if "primarySource" not in mag:
        raise DmaRuleValidationError("media_event_resolver_policy: financialMagnitudeRules missing 'primarySource'")
    if mag.get("financialAmountDirectScoringAllowedYn") is not False:
        raise DmaRuleValidationError("media_event_resolver_policy: financialMagnitudeRules.financialAmountDirectScoringAllowedYn must be false")
    _validateBandSection(mag, "financialMagnitudeRules", must_have_bands=True)

    _validateBandSection(policy["financialLikelihoodRules"], "financialLikelihoodRules", must_have_bands=True)

    th = policy["timeHorizonRules"]
    for k in ("sourcePriority", "shortMaxDays", "midMaxDays", "missingPolicy"):
        if k not in th:
            raise DmaRuleValidationError(f"media_event_resolver_policy: timeHorizonRules missing '{k}'")

    dedup = policy["eventDedupRules"]
    for k in ("mandatoryKeys", "advisoryOnlyFields", "mergePolicy", "conflictPolicy",
              "missingMandatoryKeyPolicy", "dateBucketSourcePriority", "dateBucketPrecision"):
        if k not in dedup:
            raise DmaRuleValidationError(f"media_event_resolver_policy: eventDedupRules missing '{k}'")
    if set(dedup["mandatoryKeys"]) != _KNOWN_DEDUP_MANDATORY_KEYS:
        raise DmaRuleValidationError(
            f"media_event_resolver_policy: eventDedupRules.mandatoryKeys must be exactly {sorted(_KNOWN_DEDUP_MANDATORY_KEYS)}"
        )
    if dedup["mergePolicy"] != "COMPOSITE_PLUS_MATCHING_ADVISORY_HINT":
        raise DmaRuleValidationError(
            "media_event_resolver_policy: eventDedupRules.mergePolicy must be 'COMPOSITE_PLUS_MATCHING_ADVISORY_HINT'"
        )
    if dedup["conflictPolicy"] != "CONFLICTED":
        raise DmaRuleValidationError(
            "media_event_resolver_policy: eventDedupRules.conflictPolicy must be 'CONFLICTED'"
        )
    if dedup["dateBucketPrecision"] != "DAY":
        raise DmaRuleValidationError(
            "media_event_resolver_policy: eventDedupRules.dateBucketPrecision must be 'DAY'"
        )

    rv = policy["ratioValueContract"]
    for k in ("normalization", "min", "max", "outOfRangePolicy"):
        if k not in rv:
            raise DmaRuleValidationError(f"media_event_resolver_policy: ratioValueContract missing '{k}'")
    if rv["normalization"] != "DECIMAL_RATIO_ONLY":
        raise DmaRuleValidationError(
            "media_event_resolver_policy: ratioValueContract.normalization must be 'DECIMAL_RATIO_ONLY'"
        )
    if rv["outOfRangePolicy"] != "REJECTED":
        raise DmaRuleValidationError(
            "media_event_resolver_policy: ratioValueContract.outOfRangePolicy must be 'REJECTED'"
        )

    mp = policy["missingPolicy"]
    if "requiredFactorMissing" not in mp:
        raise DmaRuleValidationError("media_event_resolver_policy: missingPolicy missing 'requiredFactorMissing'")
    if mp.get("missingAsZeroForbiddenYn") is not True:
        raise DmaRuleValidationError("media_event_resolver_policy: missingPolicy.missingAsZeroForbiddenYn must be true")


def validateKcgsScreeningPolicy(policy: Mapping[str, Any]) -> None:
    """Fail-fast structural validation for screening_policy.kcgs."""
    if not isinstance(policy, Mapping):
        raise DmaRuleValidationError("screening_policy must be a JSON object")
    kcgs = policy.get("kcgs")
    if not isinstance(kcgs, Mapping):
        raise DmaRuleValidationError("screening_policy.kcgs must be a JSON object")

    gradeOrder = kcgs.get("gradeOrderBestToWorst")
    if gradeOrder != _KCGS_GRADE_ORDER_BEST_TO_WORST:
        raise DmaRuleValidationError(
            "screening_policy.kcgs.gradeOrderBestToWorst must be exactly "
            f"{_KCGS_GRADE_ORDER_BEST_TO_WORST!r}"
        )

    gradeRisk = kcgs.get("gradeRisk")
    if not isinstance(gradeRisk, Mapping):
        raise DmaRuleValidationError("screening_policy.kcgs.gradeRisk must be a JSON object")
    if set(gradeRisk.keys()) != set(_KCGS_GRADE_ORDER_BEST_TO_WORST):
        raise DmaRuleValidationError(
            "screening_policy.kcgs.gradeRisk keys must match gradeOrderBestToWorst"
        )

    trendModifier = kcgs.get("trendModifier")
    if not isinstance(trendModifier, Mapping):
        raise DmaRuleValidationError("screening_policy.kcgs.trendModifier must be a JSON object")
    missingTrendKeys = _KCGS_TREND_MODIFIER_KEYS - set(trendModifier)
    if missingTrendKeys:
        raise DmaRuleValidationError(
            f"screening_policy.kcgs.trendModifier missing required keys: {sorted(missingTrendKeys)}"
        )
    if trendModifier.get("insufficientData") != "UNOBSERVED":
        raise DmaRuleValidationError(
            "screening_policy.kcgs.trendModifier.insufficientData must be 'UNOBSERVED'"
        )

    if kcgs.get("pillars") != _KCGS_PILLARS:
        raise DmaRuleValidationError(
            f"screening_policy.kcgs.pillars must be exactly {_KCGS_PILLARS!r}"
        )
    if kcgs.get("propagationMode") != "ALL_SUB_ISSUES_IN_PILLAR_DOMAIN":
        raise DmaRuleValidationError(
            "screening_policy.kcgs.propagationMode must be "
            "'ALL_SUB_ISSUES_IN_PILLAR_DOMAIN'"
        )
    if kcgs.get("overallGradeTraceOnlyYn") is not True:
        raise DmaRuleValidationError("screening_policy.kcgs.overallGradeTraceOnlyYn must be true")
    if kcgs.get("externalMaxEligibleYn") is not True:
        raise DmaRuleValidationError("screening_policy.kcgs.externalMaxEligibleYn must be true")
    if kcgs.get("top20BoostOnlyYn") is not False:
        raise DmaRuleValidationError("screening_policy.kcgs.top20BoostOnlyYn must be false")
    if kcgs.get("axisMode") != "SYMMETRIC_DOMAIN_SIGNAL":
        raise DmaRuleValidationError(
            "screening_policy.kcgs.axisMode must be 'SYMMETRIC_DOMAIN_SIGNAL'"
        )
    if kcgs.get("directCanonicalFinalAllowedYn") is not False:
        raise DmaRuleValidationError("screening_policy.kcgs.directCanonicalFinalAllowedYn must be false")

    for key, expected in (
        ("pillarSignalMax", 5.0),
        ("maxSubIssueBoost", 1.0),
        ("boostMultiplier", 0.20),
    ):
        value = kcgs.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != expected:
            raise DmaRuleValidationError(
                f"screening_policy.kcgs.{key} must be exactly {expected!r}, got {value!r}"
            )


def validateKisScreeningPolicy(
    policy: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    """Fail-fast structural validation for screening_policy.kis / manifest.kisFinancialResilience."""
    if not isinstance(policy, Mapping):
        raise DmaRuleValidationError("screening_policy must be a JSON object")
    kis = policy.get("kis")
    if not isinstance(kis, Mapping):
        raise DmaRuleValidationError("screening_policy.kis must be a JSON object")

    capability = kis.get("capability")
    if capability != "DATA_EXPORT_REQUIRED":
        raise DmaRuleValidationError(
            f"screening_policy.kis.capability must be 'DATA_EXPORT_REQUIRED', got {capability!r}"
        )

    reason = kis.get("reason")
    if reason != "GRID_THRESHOLDS_REQUIRED":
        raise DmaRuleValidationError(
            f"screening_policy.kis.reason must be 'GRID_THRESHOLDS_REQUIRED', got {reason!r}"
        )

    creditRating = kis.get("creditRatingPredictionAllowedYn")
    if creditRating is not False:
        raise DmaRuleValidationError(
            "screening_policy.kis.creditRatingPredictionAllowedYn must be false"
        )

    officialLabel = kis.get("officialCreditRatingLabelAllowedYn")
    if officialLabel is not False:
        raise DmaRuleValidationError(
            "screening_policy.kis.officialCreditRatingLabelAllowedYn must be false"
        )

    if not isinstance(manifest, Mapping):
        raise DmaRuleValidationError("manifest must be a JSON object")
    caps = manifest.get("capabilities")
    if not isinstance(caps, Mapping):
        raise DmaRuleValidationError("manifest.capabilities must be a JSON object")
    manifestKis = caps.get("kisFinancialResilience")
    if manifestKis != capability:
        raise DmaRuleValidationError(
            f"manifest.capabilities.kisFinancialResilience ({manifestKis!r}) "
            f"must equal screening_policy.kis.capability ({capability!r})"
        )


def validateBundle(manifest: Dict[str, Any], policies: Dict[str, Dict[str, Any]]) -> None:
    validateManifest(manifest)
    validatePolicies(policies.keys())
    validatePolicyVersions(policies)
    if "screening_policy.json" in policies:
        validateKcgsScreeningPolicy(policies["screening_policy.json"])
        validateKisScreeningPolicy(
            policies["screening_policy.json"],
            manifest,
        )
    if "media_event_resolver_policy.json" in policies:
        validateMediaEventResolverPolicy(policies["media_event_resolver_policy.json"])


def readJson(path: Path) -> Any:
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def computeConfigHash(policies: Mapping[str, Any]) -> str:
    """
    정책 파일 집합의 SHA-256 해시를 계산한다.
    파일명을 정렬한 후 각 파일의 정규화 JSON을 순서대로 해싱하여 재현 가능성을 보장한다.
    """
=======
    """Canonical JSON: keys sorted, compact separators — hash-invariant to key order and whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# STEP 0. Compute SHA-256 hash over the 6 policy files (manifest excluded).
# Input: policy dict keyed by filename.
# Output: 'sha256:<hexdigest>' string.
def computeConfigHash(policies: Mapping[str, Any]) -> str:
>>>>>>> origin/skm_test
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


<<<<<<< HEAD
def getDmaRules(forceReload: bool = False) -> RuntimeConfigV13:
    """
    v1.3 runtime config 번들을 반환한다.
    스레드 안전 캐시를 사용하며 forceReload=True이면 디스크에서 재로드한다.
    """
=======
# STEP 0. Load and cache the v1.3 slim runtime config bundle (singleton).
# Input: forceReload=True bypasses cache (used by tests).
# Output: immutable RuntimeConfigV13 snapshot.
def getDmaRules(forceReload: bool = False) -> RuntimeConfigV13:
>>>>>>> origin/skm_test
    global _cache
    with _lock:
        if _cache is None or forceReload:
            _cache = _loadBundle()
        return _cache


def resetDmaRulesForTest() -> None:
<<<<<<< HEAD
    """테스트 격리를 위해 인메모리 캐시를 초기화한다."""
=======
    """Clear the singleton cache (test helper)."""
>>>>>>> origin/skm_test
    global _cache
    with _lock:
        _cache = None


def getManifest() -> Dict[str, Any]:
<<<<<<< HEAD
    """로드된 manifest.json의 딥카피를 반환한다 (외부 변경 차단)."""
=======
>>>>>>> origin/skm_test
    return copy.deepcopy(getDmaRules().manifest)


def getAllPolicies() -> Dict[str, Dict[str, Any]]:
<<<<<<< HEAD
    """로드된 전체 정책 파일 맵의 딥카피를 반환한다."""
=======
>>>>>>> origin/skm_test
    return copy.deepcopy(getDmaRules().policies)


def getPolicy(name: str) -> Dict[str, Any]:
<<<<<<< HEAD
    """이름(확장자 선택)으로 단일 정책 파일을 조회하여 딥카피로 반환한다. 미존재 시 DmaRuleValidationError."""
=======
>>>>>>> origin/skm_test
    filename = name if name.endswith(".json") else f"{name}.json"
    filename = validatePath(filename)
    policies = getDmaRules().policies
    if filename not in policies:
        raise DmaRuleValidationError(f"Unknown runtime policy: {name!r}")
    return copy.deepcopy(policies[filename])


def getConfigHash() -> str:
<<<<<<< HEAD
    """현재 로드된 정책 번들의 SHA-256 해시 문자열을 반환한다."""
=======
>>>>>>> origin/skm_test
    return getDmaRules().configHash


def getRuleVersion() -> str:
<<<<<<< HEAD
    """로드된 번들의 ruleVersion 문자열을 반환한다."""
=======
>>>>>>> origin/skm_test
    return getDmaRules().ruleVersion


def getArchRevision() -> str:
<<<<<<< HEAD
    """로드된 번들의 architectureRevision 문자열을 반환한다."""
=======
>>>>>>> origin/skm_test
    return getDmaRules().architectureRevision


def getCapabilities() -> Dict[str, str]:
<<<<<<< HEAD
    """manifest capabilities 전체의 딥카피를 반환한다."""
=======
>>>>>>> origin/skm_test
    return copy.deepcopy(getDmaRules().capabilities)


def getCapability(name: str) -> Optional[str]:
<<<<<<< HEAD
    """지정 capability 키의 값을 반환한다. 존재하지 않으면 None을 반환한다."""
=======
>>>>>>> origin/skm_test
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
