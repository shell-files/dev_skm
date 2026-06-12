"""
DMA v1.3 MVP Slim Engine — Registry / Config Hash + AI Fact Validation tests.

Covers Acceptance Test Plan cases 1-20 + Consolidation patch case 21.
  Registry          1-12
  AI Fact Validation 13-20
  Consolidation     21

Pure unit tests. No live DB, no historical fixture, no DB connection.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import dmaruleregistry as reg
from src.utils import dmascoring as sc

# Captured before any test mutates the module global.
_ORIGINAL_CONFIG_DIR = reg.RUNTIME_CONFIG_DIR


def _baseline_bundle():
    """Read the real on-disk config into in-memory manifest + policy dicts."""
    reg.RUNTIME_CONFIG_DIR = _ORIGINAL_CONFIG_DIR
    reg.resetDmaRulesForTest()
    manifest = reg.getManifest()
    policies = reg.getAllPolicies()
    reg.resetDmaRulesForTest()
    return manifest, policies


class SlimRegistryTest(unittest.TestCase):
    def setUp(self):
        self._orig_dir = reg.RUNTIME_CONFIG_DIR
        reg.resetDmaRulesForTest()

    def tearDown(self):
        reg.RUNTIME_CONFIG_DIR = self._orig_dir
        reg.resetDmaRulesForTest()

    def _write_and_load(self, manifest, policies):
        tmp = tempfile.mkdtemp(prefix="dma_v13_cfg_")
        (Path(tmp) / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for name, body in policies.items():
            text = body if isinstance(body, str) else json.dumps(body)
            (Path(tmp) / name).write_text(text, encoding="utf-8")
        reg.RUNTIME_CONFIG_DIR = Path(tmp)
        reg.resetDmaRulesForTest()
        return reg.getDmaRules(forceReload=True)

    # 1. Manifest loads
    def test_01_manifest_loads(self):
        cfg = reg.getDmaRules()
        self.assertEqual(cfg.ruleVersion, "dma-rule-v1.3-mvp")
        self.assertEqual(cfg.architectureRevision, "R4.1-SLIM")

    # 2. Runtime policy 6-file exact set
    def test_02_policy_exact_set(self):
        cfg = reg.getDmaRules()
        self.assertEqual(set(cfg.policies.keys()), set(reg.EXPECTED_POLICY_FILES))
        self.assertEqual(len(cfg.policies), 6)

    # 3. Hash sha256: prefix
    def test_03_hash_prefix(self):
        self.assertTrue(reg.getConfigHash().startswith("sha256:"))

    # 4. Key order change -> hash unchanged
    def test_04_hash_key_order_invariant(self):
        _, policies = _baseline_bundle()
        reordered = {k: json.loads(json.dumps(dict(reversed(list(v.items()))))) for k, v in policies.items()}
        self.assertEqual(reg.computeConfigHash(policies), reg.computeConfigHash(reordered))

    # 5. Whitespace change -> hash unchanged
    def test_05_hash_whitespace_invariant(self):
        _, policies = _baseline_bundle()
        spaced = {k: json.loads(json.dumps(v, indent=4)) for k, v in policies.items()}
        self.assertEqual(reg.computeConfigHash(policies), reg.computeConfigHash(spaced))

    # 6. Rule value change -> hash changes
    def test_06_hash_value_sensitive(self):
        _, policies = _baseline_bundle()
        mutated = json.loads(json.dumps(policies))
        mutated["selection_policy.json"]["candidateThreshold"] = 4.0
        self.assertNotEqual(reg.computeConfigHash(policies), reg.computeConfigHash(mutated))

    # 7. Missing required file -> fail fast
    def test_07_missing_file_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies.pop("survey_policy.json")
        with self.assertRaises(reg.DmaRuleValidationError):
            self._write_and_load(manifest, policies)

    # 8. Invalid JSON -> fail fast
    def test_08_invalid_json_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies["screening_policy.json"] = "{ this is : not valid json,"
        with self.assertRaises(reg.DmaRuleValidationError):
            self._write_and_load(manifest, policies)

    # 9. Version mismatch -> fail fast
    def test_09_version_mismatch_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies["canonical_scoring_policy.json"]["ruleVersion"] = "dma-rule-v0.0-bad"
        with self.assertRaises(reg.DmaRuleValidationError):
            self._write_and_load(manifest, policies)
        manifest2, policies2 = _baseline_bundle()
        manifest2["ruleVersion"] = "dma-rule-v0.0-bad"
        with self.assertRaises(reg.DmaRuleValidationError):
            self._write_and_load(manifest2, policies2)

    # 10. Path traversal reject
    def test_10_path_traversal_reject(self):
        for bad in ["../secret.json", "./x.json", "a/b.json", "a\\b.json", "C:secret.json", "x.txt", "", ".."]:
            with self.assertRaises(reg.DmaRuleValidationError):
                reg.validatePath(bad)
        self.assertEqual(reg.validatePath("screening_policy.json"), "screening_policy.json")

    # 11. Deep copy returns (mutation does not leak into cache)
    def test_11_deep_copy_return(self):
        p1 = reg.getPolicy("screening_policy")
        p1["benchmark"]["NONE"] = 999
        p2 = reg.getPolicy("screening_policy")
        self.assertEqual(p2["benchmark"]["NONE"], 0)

    # 12. Cache reset / reload
    def test_12_cache_reset(self):
        a = reg.getDmaRules()
        b = reg.getDmaRules()
        self.assertIs(a, b)
        reg.resetDmaRulesForTest()
        c = reg.getDmaRules()
        self.assertIsNot(a, c)
        self.assertEqual(a.configHash, c.configHash)


class AiFactValidationTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("ai_fact_validation_policy")

    # 13. valid fact accepted
    def test_13_valid_fact_accepted(self):
        result = sc.validateAiFacts(
            {"subIssueCode": "E_CLIMATE__GHG_SCOPE12_EMISSIONS", "impactDirection": "negative", "actualYn": "TRUE"},
            self.policy,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["violations"], [])

    # 14. proposedScore reject
    def test_14_proposed_score_reject(self):
        result = sc.validateAiFacts({"proposedScore": 3}, self.policy)
        self.assertFalse(result["valid"])
        self.assertEqual(result["violations"][0]["reason"], "FORBIDDEN_FIELD")

    # 15. assignedScore reject
    def test_15_assigned_score_reject(self):
        self.assertFalse(sc.validateAiFacts({"assignedScore": 5}, self.policy)["valid"])

    # 16. scale reject
    def test_16_scale_reject(self):
        self.assertFalse(sc.validateAiFacts({"scale": 4}, self.policy)["valid"])

    # 17. likelihood reject
    def test_17_likelihood_reject(self):
        self.assertFalse(sc.validateAiFacts({"likelihood": 3}, self.policy)["valid"])

    # 18. sameEventGroupId reject
    def test_18_same_event_group_id_reject(self):
        self.assertFalse(sc.validateAiFacts({"sameEventGroupId": "g1"}, self.policy)["valid"])

    # 19. eventGroupCandidateId allowed
    def test_19_event_group_candidate_id_allowed(self):
        result = sc.validateAiFacts({"eventGroupCandidateId": "cand-1"}, self.policy)
        self.assertTrue(result["valid"])
        self.assertIn("eventGroupCandidateId", result["acceptedFacts"])

    # 20. tri-state error reject
    def test_20_tristate_error_reject(self):
        result = sc.validateAiFacts({"actualYn": "MAYBE"}, self.policy)
        self.assertFalse(result["valid"])
        self.assertEqual(result["violations"][0]["reason"], "INVALID_TRI_STATE")
        self.assertTrue(sc.validateAiFacts({"officialConfirmedYn": "UNKNOWN"}, self.policy)["valid"])

    # 21. 삭제된 모듈이 sys.modules에 없음 — 통합 후 잔재 import 없음을 확인
    def test_21_deleted_modules_not_in_sys_modules(self):
        import sys
        for mod in ("src.utils.dmarulevalidator", "src.utils.dmascreening", "src.utils.dmaselection"):
            self.assertNotIn(mod, sys.modules, f"Deleted module {mod!r} must not be loaded")


class PolicyKeyFailFastTest(unittest.TestCase):
    """SSOT strict mode — missing required policy keys must raise KeyError (cases 22-26)."""

    def setUp(self):
        reg.resetDmaRulesForTest()

    # 22. explicitNoUrgency 키 누락 → KeyError
    def test_22_explicit_no_urgency_key_required(self):
        with self.assertRaises(KeyError):
            sc.getUrgencyScore(None, {}, explicitNoUrgency=True)

    # 23. pillarSignalMax 키 누락 → KeyError
    def test_23_pillar_signal_max_key_required(self):
        scrPolicy = reg.getPolicy("screening_policy")
        kcgsBroken = {k: v for k, v in scrPolicy.items()}
        kcgsBroken["kcgs"] = {k: v for k, v in scrPolicy["kcgs"].items() if k != "pillarSignalMax"}
        with self.assertRaises(KeyError):
            sc.step2CalcKcgs("D", "flat", kcgsBroken)

    # 24. ranking.missingAxisSortValue 키 누락 → KeyError
    def test_24_missing_axis_sort_value_key_required(self):
        selPolicy = reg.getPolicy("selection_policy")
        broken = {k: v for k, v in selPolicy.items()}
        broken["ranking"] = {}
        with self.assertRaises(KeyError):
            sc.step3BuildCandidates(
                [{"subIssueCode": "X", "impactScore": 5.0, "financialScore": 3.0}], broken
            )

    # 25. recommendedTop10 키 누락 → KeyError
    def test_25_recommended_top10_key_required(self):
        selPolicy = reg.getPolicy("selection_policy")
        broken = {k: v for k, v in selPolicy.items() if k != "recommendedTop10"}
        with self.assertRaises(KeyError):
            sc.step3RunSelection(
                [{"subIssueCode": "X", "impactScore": 5.0, "financialScore": 3.0}], broken
            )

    # 26. recommendedTop5 키 누락 → KeyError
    def test_26_recommended_top5_key_required(self):
        selPolicy = reg.getPolicy("selection_policy")
        broken = {k: v for k, v in selPolicy.items() if k != "recommendedTop5"}
        with self.assertRaises(KeyError):
            sc.step3RunSelection(
                [{"subIssueCode": "X", "impactScore": 5.0, "financialScore": 3.0}], broken
            )


if __name__ == "__main__":
    unittest.main()
