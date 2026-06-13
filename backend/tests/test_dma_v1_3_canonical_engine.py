"""
DMA v1.3 MVP Slim Engine — Canonical Impact / Financial engine + Repository payload tests.

Covers Acceptance Test Plan cases:
  Canonical Impact     21-28
  Canonical Financial  29-34 (+ 34c, 34d: Ratio None/Zero patch)
  Repository Payload   57-62

Pure unit tests. No live DB, no historical fixture, no DB connection.

NOTE: ``dmarepository`` imports the project-wide Settings() singleton at module load
(via src.utils.db). The current .env predates some fields, so we set DUMMY env vars
below purely to let the module import. The v1.3 payload helpers under test are PURE
builders and never open a DB connection.
"""

import os
import sys
import unittest
from pathlib import Path

_DUMMY_ENV = {
    "host_ip": "127.0.0.1", "domain": "test", "skm_domain": "test", "file_dir": "/tmp",
    "gemini_api_key": "test", "gemini_model": "test", "kafka_server": "test", "kafka_topic": "test",
    "mail_username": "test", "mail_password": "test", "mail_from": "test@test",
    "access_token_expire_minutes": "1", "refresh_token_expire_days": "1", "invite_token_expire_days": "1",
    "redis_host": "test", "redis_port": "6379", "redis_db1": "0", "redis_db2": "1", "redis_db3": "2",
    "service_key": "test", "maria_db_user": "test", "maria_db_password": "test", "maria_db_host": "test",
    "maria_db_database": "test", "maria_db_port": "3306", "maria_db_key": "test", "cookie_key": "test",
    "APPS_SCRIPT_URL": "test", "pg_db_host": "test", "pg_db_port": "5432", "pg_db_database": "test",
    "pg_db_user": "test", "pg_db_password": "test", "ollama_url": "http://test",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import dmaruleregistry as reg
from src.utils import dmascoring as sc
from src.models.dmaengine import FactorStatusV13


class CanonicalImpactTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("canonical_scoring_policy")

    # 21. negative full observed (rulebook example -> 3.35)
    def test_21_negative_full_observed(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, scope=3, likelihood=3, irremediability=2, timeHorizon="short", policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.AUTO_CONFIRMED)
        self.assertAlmostEqual(r.score, 3.35, places=4)
        self.assertFalse(r.reweightApplied)

    # 22. positive full observed (rulebook example -> 3.75)
    def test_22_positive_full_observed(self):
        r = sc.step1CalcImpact(
            "positive", scale=4, scope=5, likelihood=3, timeHorizon="long", policy=self.policy
        )
        self.assertAlmostEqual(r.score, 3.75, places=4)

    # 23. required scale=None -> UNOBSERVED
    def test_23_required_scale_missing_unobserved(self):
        r = sc.step1CalcImpact(
            "negative", scale=None, likelihood=3, timeHorizon="short", policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.UNOBSERVED)
        self.assertIsNone(r.score)
        self.assertIn("scale", r.missingRequired)

    # 24. required likelihood=None -> UNOBSERVED
    def test_24_required_likelihood_missing_unobserved(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, likelihood=None, timeHorizon="short", policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.UNOBSERVED)
        self.assertIsNone(r.score)
        self.assertIn("likelihood", r.missingRequired)

    # 25. optional scope=None -> reweight (axis still scored)
    def test_25_optional_scope_missing_reweight(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, scope=None, likelihood=3, irremediability=2, timeHorizon="short", policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.AUTO_CONFIRMED)
        self.assertTrue(r.reweightApplied)
        self.assertIn("scope", r.missingOptional)
        self.assertIsNotNone(r.score)

    # 26. explicit scope=0 -> observed (participates, not treated as missing)
    def test_26_explicit_zero_scope_observed(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, scope=0, likelihood=3, irremediability=2, timeHorizon="short", policy=self.policy
        )
        self.assertIn("scope", r.observedFactors)
        self.assertNotIn("scope", r.missingOptional)
        self.assertFalse(r.reweightApplied)
        self.assertAlmostEqual(r.score, 0.30 * 4 + 0.25 * 0 + 0.20 * 3 + 0.15 * 2 + 0.10 * 5, places=4)

    # 27. missing urgency -> optional policy applied (reweighted, not UNOBSERVED)
    def test_27_missing_urgency_optional(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, scope=3, likelihood=3, irremediability=2, timeHorizon=None, policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.AUTO_CONFIRMED)
        self.assertIn("urgency", r.missingOptional)
        self.assertTrue(r.reweightApplied)

    # 28. explicit no urgency -> observed 0
    def test_28_explicit_no_urgency_zero(self):
        r = sc.step1CalcImpact(
            "negative", scale=4, scope=3, likelihood=3, irremediability=2,
            timeHorizon=None, explicitNoUrgency=True, policy=self.policy
        )
        self.assertIn("urgency", r.observedFactors)
        urgencyTrace = next(t for t in r.factorTraces if t.factorName == "urgency")
        self.assertEqual(urgencyTrace.observedValue, 0.0)


class CanonicalFinancialTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("canonical_scoring_policy")

    # 29. risk full observed (rulebook example -> 3.85)
    def test_29_risk_full_observed(self):
        r = sc.step1CalcFinancial(
            "risk", magnitude=4, likelihood=3, timeHorizon="short", policy=self.policy
        )
        self.assertAlmostEqual(r.score, 3.85, places=4)

    # 30. opportunity full observed
    def test_30_opportunity_full_observed(self):
        r = sc.step1CalcFinancial(
            "opportunity", magnitude=4, likelihood=3, timeHorizon="short", policy=self.policy
        )
        self.assertAlmostEqual(r.score, 0.55 * 4 + 0.25 * 3 + 0.20 * 5, places=4)

    # 31. magnitude missing -> UNOBSERVED
    def test_31_magnitude_missing_unobserved(self):
        r = sc.step1CalcFinancial("risk", magnitude=None, likelihood=3, policy=self.policy)
        self.assertEqual(r.status, FactorStatusV13.UNOBSERVED)
        self.assertIsNone(r.score)
        self.assertIn("magnitude", r.missingRequired)

    # 32. explicit magnitude 0 -> observed
    def test_32_explicit_magnitude_zero_observed(self):
        r = sc.step1CalcFinancial("risk", magnitude=0, policy=self.policy)
        self.assertEqual(r.status, FactorStatusV13.AUTO_CONFIRMED)
        self.assertIn("magnitude", r.observedFactors)
        self.assertEqual(r.score, 0.0)

    # 33. optional likelihood missing -> reweight
    def test_33_optional_likelihood_missing_reweight(self):
        r = sc.step1CalcFinancial(
            "risk", magnitude=4, likelihood=None, timeHorizon="short", policy=self.policy
        )
        self.assertEqual(r.status, FactorStatusV13.AUTO_CONFIRMED)
        self.assertIn("likelihood", r.missingOptional)
        self.assertTrue(r.reweightApplied)
        self.assertAlmostEqual(r.score, (0.45 * 4 + 0.20 * 5) / 0.65, places=4)

    # 34. ratio band boundaries
    def test_34_ratio_band_boundaries(self):
        bands = self.policy["financialMagnitudeRatioBands"]
        cases = {0.0: 0, 0.0009: 1, 0.001: 2, 0.004: 2, 0.005: 3, 0.009: 3,
                 0.01: 4, 0.029: 4, 0.03: 5, 0.5: 5}
        for ratio, expected in cases.items():
            self.assertEqual(sc.getRatioScore(ratio, bands), expected, msg=f"ratio={ratio}")

    # 34b. dominant magnitude tie-break
    def test_34b_dominant_magnitude_tiebreak(self):
        value, channel = sc.getDominantMagnitude(
            {"costMagnitude": 4, "legalRegulatoryMagnitude": 4, "revenueMagnitude": 2}
        )
        self.assertEqual((value, channel), (4.0, "legalRegulatoryMagnitude"))
        self.assertEqual(sc.getDominantMagnitude({"costMagnitude": None}), (None, None))

    # 34c. ratio=None → None (UNOBSERVED) — Phase A.1 Correctness Patch
    def test_34c_ratio_none_is_unobserved(self):
        bands = self.policy["financialMagnitudeRatioBands"]
        result = sc.getRatioScore(None, bands)
        self.assertIsNone(result, "ratio=None must return None (UNOBSERVED), not 0")

    # 34d. ratio=0 → 0 (Explicit Zero) — Phase A.1 Correctness Patch
    def test_34d_ratio_zero_is_explicit_zero(self):
        bands = self.policy["financialMagnitudeRatioBands"]
        result = sc.getRatioScore(0.0, bands)
        self.assertEqual(result, 0, "ratio=0 must return 0 (explicit zero exposure)")


class RepositoryPayloadTest(unittest.TestCase):
    """Repository payload trace helpers (cases 57-62). Pure builders; no DB write."""

    def setUp(self):
        reg.resetDmaRulesForTest()
        from src.utils import dmarepository as repo
        self.repo = repo

    # 57. ruleVersion stored
    def test_57_rule_version_stored(self):
        payload = self.repo.step4BuildTrace(subIssueCode="S_SAFETY__OHS_MANAGEMENT")
        self.assertEqual(payload["ruleVersion"], "dma-rule-v1.3-mvp")
        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")

    # 58. configHash stored
    def test_58_config_hash_stored(self):
        payload = self.repo.step4BuildTrace(subIssueCode="S_SAFETY__OHS_MANAGEMENT")
        self.assertTrue(payload["configHash"].startswith("sha256:"))
        self.assertEqual(payload["configHash"], reg.getConfigHash())

    # 59. extractedFacts / factorTrace are distinct fields
    def test_59_facts_and_trace_separated(self):
        facts = {"subIssueCode": "S_SAFETY__OHS_MANAGEMENT", "impactDirection": "negative"}
        trace = [{"factorName": "scale", "status": "AUTO_CONFIRMED", "decisionSource": "RULE_AUTO", "observedValue": 4.0}]
        payload = self.repo.step4BuildTrace(
            subIssueCode="S_SAFETY__OHS_MANAGEMENT", extractedFacts=facts, factorTrace=trace
        )
        self.assertIn("extractedFacts", payload)
        self.assertIn("factorTrace", payload)
        self.assertIsNotNone(payload["extractedFacts"])
        self.assertEqual(len(payload["factorTrace"]), 1)
        self.assertNotIn("proposedScore", payload["extractedFacts"])

    # 60. legacy payload is read-only (detected, not parsed as v1.3)
    def test_60_legacy_read_only(self):
        legacy = {"subIssueCode": "X", "sourceStep": "media_external", "impactScore05": 3.0}
        self.assertTrue(self.repo.isLegacyPayload(legacy))
        self.assertIsNone(self.repo.step4ReadTrace(legacy))
        v13 = self.repo.step4BuildTrace(subIssueCode="X")
        self.assertFalse(self.repo.isLegacyPayload(v13))
        self.assertIsNotNone(self.repo.step4ReadTrace(v13))

    # 61. legacy score reuse forbidden
    def test_61_legacy_score_reuse_forbidden(self):
        legacy = {"subIssueCode": "X", "impactScore05": 3.0, "financialScore05": 4.0}
        updated = self.repo.step4UpdateTrace(
            legacy, [{"factorName": "scale", "status": "AUTO_CONFIRMED", "decisionSource": "RULE_AUTO", "observedValue": 4.0}]
        )
        compat = updated["legacyCompatibility"]
        self.assertFalse(compat["legacyScoreReusedYn"])
        self.assertFalse(compat["legacyMigratedYn"])
        self.assertTrue(compat["legacyScoringPayloadPresentYn"])
        self.assertNotIn("impactScore05", updated)
        self.assertNotIn("financialScore05", updated)

    # 62. legacy update forbidden (no in-place factor-trace update on legacy payload)
    def test_62_legacy_update_forbidden(self):
        legacy = {"subIssueCode": "X", "impactScore05": 3.0}
        with self.assertRaises(ValueError):
            self.repo.appendFactorTrace(legacy, [])
        updated = self.repo.step4UpdateTrace(legacy, [])
        self.assertFalse(updated["legacyCompatibility"]["legacyUpdatedYn"])


if __name__ == "__main__":
    unittest.main()
