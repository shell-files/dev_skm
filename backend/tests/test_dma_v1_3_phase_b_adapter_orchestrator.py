"""
DMA v1.3 Phase B adapter/orchestrator foundation tests.

Pure unit tests. No DB write, API smoke, Redis, Kafka, Docker, or service runtime
migration path is exercised.
"""

import copy
import importlib
import json
import os
import sys
import tempfile
import types
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
for _key, _value in _DUMMY_ENV.items():
    os.environ.setdefault(_key, _value)

if "mariadb" not in sys.modules:
    mariadb = types.ModuleType("mariadb")
    mariadb.Error = Exception
    mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = mariadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.dmaengine import ExtractedFactsV13, ScorePurposeV13  # noqa: E402
from src.utils import dmaruleregistry as reg  # noqa: E402
from src.utils import dmascoring as sc  # noqa: E402


_ORIGINAL_CONFIG_DIR = reg.RUNTIME_CONFIG_DIR


def baselineBundle():
    reg.RUNTIME_CONFIG_DIR = _ORIGINAL_CONFIG_DIR
    reg.resetDmaRulesForTest()
    manifest = reg.getManifest()
    policies = reg.getAllPolicies()
    reg.resetDmaRulesForTest()
    return manifest, policies


class PhaseBRegistryStrictTest(unittest.TestCase):
    def setUp(self):
        self.originalDir = reg.RUNTIME_CONFIG_DIR
        reg.resetDmaRulesForTest()

    def tearDown(self):
        reg.RUNTIME_CONFIG_DIR = self.originalDir
        reg.resetDmaRulesForTest()

    def writeAndLoad(self, manifest, policies):
        tmp = tempfile.mkdtemp(prefix="dma_v13_phase_b_")
        Path(tmp, "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for name, body in policies.items():
            Path(tmp, name).write_text(json.dumps(body), encoding="utf-8")
        reg.RUNTIME_CONFIG_DIR = Path(tmp)
        reg.resetDmaRulesForTest()
        return reg.getDmaRules(forceReload=True)

    def test_manifest_capabilities_missing_fails_fast(self):
        manifest, policies = baselineBundle()
        manifest.pop("capabilities")
        with self.assertRaises(reg.DmaRuleValidationError):
            self.writeAndLoad(manifest, policies)

    def test_manifest_required_capability_missing_fails_fast(self):
        manifest, policies = baselineBundle()
        manifest["capabilities"].pop("mediaEventCanonicalAdapter")
        with self.assertRaises(reg.DmaRuleValidationError):
            self.writeAndLoad(manifest, policies)

    def test_screening_policy_has_no_capabilities_block(self):
        policy = reg.getPolicy("screening_policy")
        self.assertNotIn("capabilities", policy)
        caps = reg.getCapabilities()
        self.assertEqual(set(reg.EXPECTED_CAPABILITY_KEYS) - set(caps), set())

    def test_external_aggregation_additive_key_required(self):
        policy = reg.getPolicy("screening_policy")
        broken = copy.deepcopy(policy)
        broken["externalAggregation"].pop("additiveYn")
        with self.assertRaises(KeyError):
            sc.step2CalcExternalMax([], broken)

    def test_ai_validation_policy_keys_required(self):
        with self.assertRaises(KeyError):
            sc.validateAiFacts({}, {})

    def test_selection_governance_keys_required(self):
        policy = reg.getPolicy("selection_policy")
        broken = copy.deepcopy(policy)
        broken["governanceGate"].pop("manualSelectionActionsAllowed")
        with self.assertRaises(KeyError):
            sc.step3ApplyDecision({"subIssueCode": "S1", "selectionType": sc.SELECTION_TYPE_MANUAL_ADD}, broken)


class PhaseBRenameBoundaryTest(unittest.TestCase):
    def test_financial_basis_repository_import_is_renamed(self):
        oldName = "src.utils." + "dma" + "financialrepository"
        sys.modules.pop(oldName, None)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module(oldName)
        module = importlib.import_module("src.utils.financialbasisrepository")
        self.assertTrue(hasattr(module, "getBasis"))

    def test_renamed_imports_are_used_by_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        exposure = Path(root, "src/services/materialities/financialexposure.py").read_text(encoding="utf-8")
        workflow = Path(root, "src/utils/reportworkflowrepository.py").read_text(encoding="utf-8")
        self.assertIn("financialbasisrepository", exposure)
        self.assertIn("financialbasisrepository", workflow)
        oldName = "dma" + "financialrepository"
        self.assertNotIn(oldName, exposure)
        self.assertNotIn(oldName, workflow)


class PhaseBAdapterTest(unittest.TestCase):
    def test_benchmark_normalizer_returns_fact_only_payload(self):
        from src.services.benchmarks import adapter

        facts = adapter.step0NormalizeBenchmarkFacts([{
            "subIssueCode": "G0-02",
            "rawIssueLabel": "finance",
            "displaySubIssueName": "Finance",
            "evidenceSpans": ["evidence sentence"],
            "classificationConfidence": 0.82,
            "impactFactor": {"scale": 5},
            "impactScore": 4.5,
        }], fileId=17, sourceType="leader_sr", aiPolicy=reg.getPolicy("ai_fact_validation_policy"))
        self.assertEqual(len(facts), 1)
        self.assertIsInstance(facts[0], ExtractedFactsV13)
        dumped = facts[0].model_dump(mode="json", by_alias=False)
        for forbidden in ("impactFactor", "financialFactor", "impactScore", "financialScore", "impactScore05"):
            self.assertNotIn(forbidden, dumped)
        self.assertEqual(dumped["rawMetadata"]["teSrFileId"], 17)
        self.assertEqual(dumped["rawMetadata"]["sourceType"], "leader_sr")

    def test_media_normalizer_preserves_provenance_without_event_guess(self):
        from src.services.medias import adapter

        facts = adapter.step0NormalizeMediaFacts([{
            "bestSubIssueId": "G0-02",
            "bestSubIssueNameKr": "Finance",
            "bestSimilarityScore": 0.71,
            "chunk": "quoted body",
            "title": "news title",
            "url": "https://example.test/news",
            "source": "wire",
            "publishedAt": "2026-06-11",
            "issueSimilarityMatches": [{"issue": "G0-02"}],
        }])
        self.assertEqual(len(facts), 1)
        self.assertIsNone(facts[0].eventType)
        self.assertEqual(facts[0].sourceType, "news")
        self.assertEqual(facts[0].rawMetadata["similarityScore"], 0.71)
        self.assertEqual(facts[0].rawMetadata["sourceUrl"], "https://example.test/news")
        # Provider metadata (C2.0)
        self.assertEqual(facts[0].rawMetadata["mediaExternalSourceType"], "news")
        self.assertEqual(facts[0].rawMetadata["providerKey"], "wire")

    def test_survey_normalizer_preserves_null_and_skips_unmapped_rows(self):
        from src.services.surveys import adapter

        rows = [
            {"responseKey": "R1", "questionKey": "Q1", "respondentGroup": "employee", "normalizedScore": None},
            {"responseKey": "R2", "questionKey": "Q2", "respondentGroup": "employee", "normalizedScore": 4},
            {"responseKey": "R3", "questionKey": "Q3", "respondentGroup": "employee", "normalizedScore": 5},
        ]
        questionMap = {
            "Q1": {"subIssueCode": "S1", "mappedAxis": "impact"},
            "Q2": {"subIssueCode": "S1"},
            "Q3": {"mappedAxis": "financial"},
        }
        bundle = adapter.step0NormalizeSurveyRows(rows, questionMap)
        normalized = bundle["normalizedRows"]
        skipped = bundle["skippedRows"]
        self.assertEqual(len(normalized), 1)
        self.assertEqual(len(skipped), 2)
        self.assertIsNone(normalized[0]["normalizedScore"])
        self.assertEqual(normalized[0]["mappedAxis"], "impact")

    def test_benchmark_original_result_top_level_forbidden_fields_removed(self):
        from src.services.benchmarks import adapter

        facts = adapter.step0NormalizeBenchmarkFacts([{
            "subIssueCode": "S1",
            "impactFactor": {"scale": 5},
            "financialFactor": {"magnitude": 4},
            "impactScore": 4.5,
            "financialScore": 3.8,
            "similarityScore": 0.82,
        }], fileId=1, sourceType="leader_sr", aiPolicy=reg.getPolicy("ai_fact_validation_policy"))
        original = facts[0].rawMetadata["originalResult"]
        for forbidden in ("impactFactor", "financialFactor", "impactScore", "financialScore"):
            self.assertNotIn(forbidden, original)
        self.assertEqual(original["similarityScore"], 0.82)

    def test_benchmark_original_result_nested_forbidden_fields_removed(self):
        from src.services.benchmarks import adapter

        facts = adapter.step0NormalizeBenchmarkFacts([{
            "subIssueCode": "S1",
            "nested": {"proposedScore": 5, "safeText": "keep"},
        }], fileId=1, sourceType="leader_sr", aiPolicy=reg.getPolicy("ai_fact_validation_policy"))
        nested = facts[0].rawMetadata["originalResult"]["nested"]
        self.assertNotIn("proposedScore", nested)
        self.assertEqual(nested["safeText"], "keep")

    def test_survey_skip_reason_mapped_axis_missing(self):
        from src.services.surveys import adapter

        bundle = adapter.step0NormalizeSurveyRows(
            [{"responseKey": "R1", "questionKey": "Q1", "respondentGroup": "employee"}],
            {"Q1": {"subIssueCode": "S1"}},
        )
        self.assertEqual(bundle["normalizedRows"], [])
        self.assertEqual(bundle["skippedRows"][0]["skipReason"], "MAPPED_AXIS_MISSING")

    def test_survey_skip_reason_sub_issue_missing(self):
        from src.services.surveys import adapter

        bundle = adapter.step0NormalizeSurveyRows(
            [{"responseKey": "R1", "questionKey": "Q1", "respondentGroup": "employee"}],
            {"Q1": {"mappedAxis": "impact"}},
        )
        self.assertEqual(bundle["normalizedRows"], [])
        self.assertEqual(bundle["skippedRows"][0]["skipReason"], "SUB_ISSUE_CODE_MISSING")

    def test_survey_skip_reason_respondent_group_invalid(self):
        from src.services.surveys import adapter

        bundle = adapter.step0NormalizeSurveyRows(
            [{"responseKey": "R1", "questionKey": "Q1", "respondentGroup": "vendor"}],
            {"Q1": {"subIssueCode": "S1", "mappedAxis": "impact"}},
        )
        self.assertEqual(bundle["normalizedRows"], [])
        self.assertEqual(bundle["skippedRows"][0]["skipReason"], "RESPONDENT_GROUP_INVALID")

    def test_survey_skip_reason_raw_row_invalid(self):
        from src.services.surveys import adapter

        bundle = adapter.step0NormalizeSurveyRows(["bad-row"], {})
        self.assertEqual(bundle["normalizedRows"], [])
        self.assertEqual(bundle["skippedRows"][0], {
            "rowIndex": 0,
            "responseKey": None,
            "questionKey": None,
            "skipReason": "RAW_ROW_INVALID",
        })


class PhaseBSurveyOverlayTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("survey_policy")

    def test_survey_overlay_separates_axes_and_excludes_nulls(self):
        rows = [
            {"mappedAxis": "impact", "respondentGroup": "employee", "normalizedScore": 4.0},
            {"mappedAxis": "impact", "respondentGroup": "management", "normalizedScore": None},
            {"mappedAxis": "impact", "respondentGroup": "external", "normalizedScore": 2.0},
            {"mappedAxis": "financial", "respondentGroup": "employee", "normalizedScore": 3.0},
            {"mappedAxis": "financial", "respondentGroup": "management", "normalizedScore": 5.0},
            {"mappedAxis": "financial", "respondentGroup": "external", "normalizedScore": None},
        ]
        result = sc.step2CalcSurveyOverlay(rows, self.policy)
        self.assertAlmostEqual(result["impactOverlay"], ((4.0 * 0.35) + (2.0 * 0.25)) / 0.60, places=4)
        self.assertAlmostEqual(result["financialOverlay"], ((3.0 * 0.20) + (5.0 * 0.50)) / 0.70, places=4)
        self.assertEqual(result["impactObservedCount"], 2)
        self.assertEqual(result["financialObservedCount"], 2)
        self.assertEqual(result["scorePurpose"], ScorePurposeV13.STAKEHOLDER_OVERLAY.value)
        self.assertNotIn("impactScore", rows[0])


class PhaseBRegulationStrictTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("screening_policy")

    def test_regulation_rule_card_impact_key_required(self):
        broken = copy.deepcopy(self.policy)
        broken["regulation"]["CSRD"]["DIRECT_MANDATORY"].pop("impact")
        with self.assertRaises(KeyError):
            sc.step2CalcRegulation("CSRD", "DIRECT_MANDATORY", broken)

    def test_regulation_rule_card_financial_key_required(self):
        broken = copy.deepcopy(self.policy)
        broken["regulation"]["CSRD"]["DIRECT_MANDATORY"].pop("financial")
        with self.assertRaises(KeyError):
            sc.step2CalcRegulation("CSRD", "DIRECT_MANDATORY", broken)


class PhaseBOrchestratorTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()

    def test_orchestrator_source_is_isolated(self):
        root = Path(__file__).resolve().parents[1]
        source = Path(root, "src/services/materialities/orchestrator.py").read_text(encoding="utf-8")
        for banned in (
            "src.utils.dmaaggregator",
            "src.services.medias.baseline",
            "src.utils.db",
            "saveSignals",
            "recalcStage",
            "recalcFinal",
        ):
            self.assertNotIn(banned, source)

    def test_orchestrator_public_surface_is_seven_functions(self):
        from src.services.materialities import orchestrator

        functions = sorted(
            name for name, value in vars(orchestrator).items()
            if callable(value)
            and getattr(value, "__module__", None) == orchestrator.__name__
            and not name.startswith("_")
        )
        self.assertEqual(functions, [
            "step0BuildFactTrace",
            "step1BuildMediaNewsCanonicalPayloads",
            "step1RunCanonical",
            "step2BuildBenchmarkScreeningPayloads",
            "step2ResolveBenchmarkObservation",
            "step2RunScreening",
            "step3RunSelection",
        ])

    def test_step1_run_canonical_builds_payload(self):
        from src.services.materialities import orchestrator

        payload = orchestrator.step1RunCanonical(
            subIssueCode="S1",
            sourceChannel="unit",
            impactInput={
                "impactDirection": "negative",
                "scale": 4,
                "scope": 3,
                "likelihood": 3,
                "irremediability": 2,
                "timeHorizon": "short",
            },
        )
        self.assertEqual(payload["scorePurpose"], ScorePurposeV13.CANONICAL_IRO.value)
        self.assertEqual(payload["sourceChannel"], "unit")
        self.assertEqual(len(payload["axisScores"]), 1)
        self.assertEqual(payload["ruleVersion"], reg.EXPECTED_RULE_VERSION)
        self.assertTrue(payload["configHash"].startswith("sha256:"))

    def test_step2_run_screening_channels_build_payloads(self):
        from src.services.materialities import orchestrator

        benchmark = orchestrator.step2RunScreening("benchmark", {"observation": "BLIND_SPOT"})
        regulation = orchestrator.step2RunScreening("regulation", {"regime": "CSRD", "applicability": "DIRECT_MANDATORY"})
        kcgs = orchestrator.step2RunScreening("kcgs", {"grade": "D", "trend": "flat"})
        external = orchestrator.step2RunScreening("externalMax", {
            "signals": [benchmark["screeningTrace"][0], regulation["screeningTrace"][0]],
        })
        survey = orchestrator.step2RunScreening("surveyOverlay", {
            "normalizedRows": [{"mappedAxis": "impact", "respondentGroup": "employee", "normalizedScore": 5.0}],
        })

        self.assertEqual(benchmark["screeningTrace"][0]["impactSignal"], 4.0)
        self.assertEqual(regulation["screeningTrace"][0]["financialSignal"], 4.0)
        self.assertEqual(kcgs["screeningTrace"][0]["channel"], "kcgs_pillar_boost")
        self.assertIsNone(kcgs["screeningTrace"][0]["impactSignal"])
        self.assertIsNone(kcgs["screeningTrace"][0]["financialSignal"])
        self.assertEqual(external["screeningTrace"][0]["financialSignal"], 4.0)
        self.assertEqual(survey["scorePurpose"], ScorePurposeV13.STAKEHOLDER_OVERLAY.value)

    def test_kcgs_payload_is_boost_only(self):
        from src.services.materialities import orchestrator

        payload = orchestrator.step2RunScreening("kcgs", {"grade": "D", "trend": "flat"})
        trace = payload["screeningTrace"][0]
        self.assertEqual(trace["channel"], "kcgs_pillar_boost")
        self.assertIsNone(trace["impactSignal"])
        self.assertIsNone(trace["financialSignal"])
        self.assertIn("pillarSignal", trace["rawInputs"])
        self.assertIn("subIssueBoost", trace["rawInputs"])
        self.assertIs(trace["rawInputs"]["directCanonicalFinalAllowedYn"], False)

    def test_kcgs_trace_does_not_contribute_to_external_max(self):
        from src.services.materialities import orchestrator

        kcgs = orchestrator.step2RunScreening("kcgs", {"grade": "D", "trend": "flat"})
        external = orchestrator.step2RunScreening("externalMax", {"signals": [kcgs["screeningTrace"][0]]})
        trace = external["screeningTrace"][0]
        self.assertIsNone(trace["impactSignal"])
        self.assertIsNone(trace["financialSignal"])

    def test_step3_run_selection_delegates_to_selection_policy(self):
        from src.services.materialities import orchestrator

        result = orchestrator.step3RunSelection([
            {"subIssueCode": "LOW", "impactScore": 2.0, "financialScore": 2.0},
            {"subIssueCode": "HIGH", "impactScore": 4.0, "financialScore": 3.0},
        ])
        self.assertEqual([item["subIssueCode"] for item in result["recommendedTop10"]], ["HIGH"])


if __name__ == "__main__":
    unittest.main()
