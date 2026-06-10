"""
DMA v1.3 MVP Slim Engine — Registry / Validator / Config Hash + AI Fact Validation tests.

Covers Acceptance Test Plan cases 1-20:
  Registry          1-12
  AI Fact Validation 13-20

Pure unit tests. No live DB, no historical fixture, no DB connection.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import dmaruleregistry as reg
from src.utils import dmarulevalidator as val
from src.utils import dmascoring as sc

# Captured before any test mutates the module global, so baselines always read the
# real installed config regardless of test ordering.
_ORIGINAL_CONFIG_DIR = reg.RUNTIME_CONFIG_DIR


def _baseline_bundle():
    """Read the real on-disk config into in-memory manifest + policy dicts."""
    reg.RUNTIME_CONFIG_DIR = _ORIGINAL_CONFIG_DIR
    reg.reset_cache()
    manifest = reg.get_manifest()
    policies = reg.get_all_policies()
    reg.reset_cache()
    return manifest, policies


class SlimRegistryTest(unittest.TestCase):
    def setUp(self):
        self._orig_dir = reg.RUNTIME_CONFIG_DIR
        reg.reset_cache()

    def tearDown(self):
        reg.RUNTIME_CONFIG_DIR = self._orig_dir
        reg.reset_cache()

    # -- helper: write a manifest + policy set into a temp dir and load it ----------
    def _write_and_load(self, manifest, policies):
        tmp = tempfile.mkdtemp(prefix="dma_v13_cfg_")
        (Path(tmp) / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for name, body in policies.items():
            # body may already be a string (to inject invalid JSON)
            text = body if isinstance(body, str) else json.dumps(body)
            (Path(tmp) / name).write_text(text, encoding="utf-8")
        reg.RUNTIME_CONFIG_DIR = Path(tmp)
        reg.reset_cache()
        return reg.load_runtime_config(force_reload=True)

    # 1. Manifest loads
    def test_01_manifest_loads(self):
        cfg = reg.load_runtime_config()
        self.assertEqual(cfg.rule_version, "dma-rule-v1.3-mvp")
        self.assertEqual(cfg.architecture_revision, "R4.1-SLIM")

    # 2. Runtime policy 5-file exact set
    def test_02_policy_exact_set(self):
        cfg = reg.load_runtime_config()
        self.assertEqual(set(cfg.policies.keys()), set(val.EXPECTED_POLICY_FILES))
        self.assertEqual(len(cfg.policies), 5)

    # 3. Hash sha256: prefix
    def test_03_hash_prefix(self):
        self.assertTrue(reg.get_config_hash().startswith("sha256:"))

    # 4. Key order change -> hash unchanged
    def test_04_hash_key_order_invariant(self):
        _, policies = _baseline_bundle()
        reordered = {k: json.loads(json.dumps(dict(reversed(list(v.items()))))) for k, v in policies.items()}
        self.assertEqual(reg.compute_config_hash(policies), reg.compute_config_hash(reordered))

    # 5. Whitespace change -> hash unchanged
    def test_05_hash_whitespace_invariant(self):
        _, policies = _baseline_bundle()
        # Re-serialize with extra whitespace then re-parse: same semantic content.
        spaced = {k: json.loads(json.dumps(v, indent=4)) for k, v in policies.items()}
        self.assertEqual(reg.compute_config_hash(policies), reg.compute_config_hash(spaced))

    # 6. Rule value change -> hash changes
    def test_06_hash_value_sensitive(self):
        _, policies = _baseline_bundle()
        mutated = json.loads(json.dumps(policies))
        mutated["selection_policy.json"]["candidateThreshold"] = 4.0
        self.assertNotEqual(reg.compute_config_hash(policies), reg.compute_config_hash(mutated))

    # 7. Missing required file -> fail fast
    def test_07_missing_file_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies.pop("survey_policy.json")  # remove a required file
        with self.assertRaises(val.DmaRuleValidationError):
            self._write_and_load(manifest, policies)

    # 8. Invalid JSON -> fail fast
    def test_08_invalid_json_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies["screening_policy.json"] = "{ this is : not valid json,"
        with self.assertRaises(val.DmaRuleValidationError):
            self._write_and_load(manifest, policies)

    # 9. Version mismatch -> fail fast
    def test_09_version_mismatch_fail_fast(self):
        manifest, policies = _baseline_bundle()
        policies["canonical_scoring_policy.json"]["ruleVersion"] = "dma-rule-v0.0-bad"
        with self.assertRaises(val.DmaRuleValidationError):
            self._write_and_load(manifest, policies)
        # also a manifest-level mismatch
        manifest2, policies2 = _baseline_bundle()
        manifest2["ruleVersion"] = "dma-rule-v0.0-bad"
        with self.assertRaises(val.DmaRuleValidationError):
            self._write_and_load(manifest2, policies2)

    # 10. Path traversal reject
    def test_10_path_traversal_reject(self):
        for bad in ["../secret.json", "./x.json", "a/b.json", "a\\b.json", "C:secret.json", "x.txt", "", ".."]:
            with self.assertRaises(val.DmaRuleValidationError):
                val.validate_config_filename(bad)
        # a clean name is accepted
        self.assertEqual(val.validate_config_filename("screening_policy.json"), "screening_policy.json")

    # 11. Deep copy returns (mutation does not leak into cache)
    def test_11_deep_copy_return(self):
        p1 = reg.get_policy("screening_policy")
        p1["benchmark"]["NONE"] = 999
        p2 = reg.get_policy("screening_policy")
        self.assertEqual(p2["benchmark"]["NONE"], 0)

    # 12. Cache reset / reload
    def test_12_cache_reset(self):
        a = reg.load_runtime_config()
        b = reg.load_runtime_config()
        self.assertIs(a, b)  # singleton cached
        reg.reset_cache()
        c = reg.load_runtime_config()
        self.assertIsNot(a, c)  # fresh instance after reset
        self.assertEqual(a.config_hash, c.config_hash)  # same content


class AiFactValidationTest(unittest.TestCase):
    def setUp(self):
        reg.reset_cache()
        self.policy = reg.get_policy("ai_fact_validation_policy")

    # 13. valid fact accepted
    def test_13_valid_fact_accepted(self):
        result = sc.validate_ai_extracted_facts_v13(
            {"subIssueCode": "E_CLIMATE__GHG_SCOPE12_EMISSIONS", "impactDirection": "negative", "actualYn": "TRUE"},
            self.policy,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["violations"], [])

    # 14. proposedScore reject
    def test_14_proposed_score_reject(self):
        result = sc.validate_ai_extracted_facts_v13({"proposedScore": 3}, self.policy)
        self.assertFalse(result["valid"])
        self.assertEqual(result["violations"][0]["reason"], "FORBIDDEN_FIELD")

    # 15. assignedScore reject
    def test_15_assigned_score_reject(self):
        self.assertFalse(sc.validate_ai_extracted_facts_v13({"assignedScore": 5}, self.policy)["valid"])

    # 16. scale reject
    def test_16_scale_reject(self):
        self.assertFalse(sc.validate_ai_extracted_facts_v13({"scale": 4}, self.policy)["valid"])

    # 17. likelihood reject
    def test_17_likelihood_reject(self):
        self.assertFalse(sc.validate_ai_extracted_facts_v13({"likelihood": 3}, self.policy)["valid"])

    # 18. sameEventGroupId reject
    def test_18_same_event_group_id_reject(self):
        self.assertFalse(sc.validate_ai_extracted_facts_v13({"sameEventGroupId": "g1"}, self.policy)["valid"])

    # 19. eventGroupCandidateId allowed
    def test_19_event_group_candidate_id_allowed(self):
        result = sc.validate_ai_extracted_facts_v13({"eventGroupCandidateId": "cand-1"}, self.policy)
        self.assertTrue(result["valid"])
        self.assertIn("eventGroupCandidateId", result["acceptedFacts"])

    # 20. tri-state error reject
    def test_20_tristate_error_reject(self):
        result = sc.validate_ai_extracted_facts_v13({"actualYn": "MAYBE"}, self.policy)
        self.assertFalse(result["valid"])
        self.assertEqual(result["violations"][0]["reason"], "INVALID_TRI_STATE")
        # valid tri-state values still pass
        self.assertTrue(sc.validate_ai_extracted_facts_v13({"officialConfirmedYn": "UNKNOWN"}, self.policy)["valid"])


if __name__ == "__main__":
    unittest.main()
