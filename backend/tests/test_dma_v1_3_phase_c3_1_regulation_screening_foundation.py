"""
DMA v1.3 Phase C3.1 regulation screening foundation tests.

Pure unit tests. No DB write, API smoke, Redis, Kafka, Docker, external API, or
runtime service hook is exercised.
"""

import inspect
import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path

from pydantic import ValidationError


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

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.models.dmaengine import (  # noqa: E402
    RegulationApplicabilityInputV13,
    RegulationSubIssueMappingSeedV13,
)
from src.services.materialities import orchestrator  # noqa: E402
from src.utils import dmascoring  # noqa: E402
from src.utils.subissuemaster import subissueMaster  # noqa: E402


CSRD_SUB = "G_DATA_GOVERNANCE__DISCLOSURE_ASSURANCE"
CBAM_SUB = "E_CLIMATE__GHG_SCOPE12_EMISSIONS"
DPP_SUB = "E_CIRCULARITY__RECYCLING_RECOVERY"


def approvedInput(regime="CSRD", applicability="DIRECT_MANDATORY", companyId=1001, reportingYear=2026):
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "regime": regime,
        "applicability": applicability,
        "inputMethod": "MANUAL",
        "sourceDocumentRef": "board-minutes-1",
        "reviewStatus": "APPROVED",
        "reviewerComment": "approved for screening foundation test",
    }


def approvedMapping(regime="CSRD", subIssueCode=CSRD_SUB):
    return {
        "regime": regime,
        "subIssueCode": subIssueCode,
        "mappingReason": "screening seed relation",
        "activeYn": True,
        "reviewStatus": "APPROVED",
    }


def buildPayloads(inputs=None, mappings=None):
    return orchestrator.step2BuildRegulationScreeningPayloads(
        inputs if inputs is not None else [approvedInput()],
        mappings if mappings is not None else [approvedMapping()],
    )


class PhaseC31ExistingRuleCardReuseTest(unittest.TestCase):
    def signal(self, regime, applicability):
        payload = orchestrator.step2RunScreening("regulation", {
            "regime": regime,
            "applicability": applicability,
            "subIssueCode": CSRD_SUB,
        })
        return payload["screeningTrace"][0]

    def test_01_csrd_direct_mandatory_reuses_existing_rule_card(self):
        trace = self.signal("CSRD", "DIRECT_MANDATORY")
        self.assertEqual(trace["impactSignal"], 3.0)
        self.assertEqual(trace["financialSignal"], 4.0)

    def test_02_cbam_direct_mandatory_reuses_existing_rule_card(self):
        trace = self.signal("CBAM", "DIRECT_MANDATORY")
        self.assertEqual(trace["impactSignal"], 4.0)
        self.assertEqual(trace["financialSignal"], 5.0)

    def test_03_dpp_direct_mandatory_reuses_existing_rule_card(self):
        trace = self.signal("DPP", "DIRECT_MANDATORY")
        self.assertEqual(trace["impactSignal"], 4.0)
        self.assertEqual(trace["financialSignal"], 4.0)

    def test_04_csrd_material_value_chain_reuses_existing_rule_card(self):
        trace = self.signal("CSRD", "MATERIAL_VALUE_CHAIN")
        self.assertEqual(trace["impactSignal"], 2.0)
        self.assertEqual(trace["financialSignal"], 3.0)

    def test_05_cbam_monitoring_only_reuses_existing_rule_card(self):
        trace = self.signal("CBAM", "MONITORING_ONLY")
        self.assertEqual(trace["impactSignal"], 1.0)
        self.assertEqual(trace["financialSignal"], 2.0)

    def test_06_dpp_not_applicable_is_explicit_zero_observed(self):
        trace = self.signal("DPP", "NOT_APPLICABLE")
        self.assertEqual(trace["impactSignal"], 0.0)
        self.assertEqual(trace["financialSignal"], 0.0)
        self.assertEqual(trace["status"], dmascoring.STATUS_OBSERVED)

    def test_07_unknown_is_unobserved(self):
        trace = self.signal("CSRD", "UNKNOWN")
        self.assertIsNone(trace["impactSignal"])
        self.assertIsNone(trace["financialSignal"])
        self.assertEqual(trace["status"], dmascoring.STATUS_UNOBSERVED)


class PhaseC31DtoFailFastTest(unittest.TestCase):
    def test_08_invalid_regime_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(inputs=[approvedInput(regime="ISSB")])

    def test_09_invalid_applicability_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(inputs=[approvedInput(applicability="AUTO_DIRECT")])

    def test_10_invalid_input_method_fails_fast(self):
        item = approvedInput()
        item["inputMethod"] = "AI_INFERRED"
        with self.assertRaises(ValueError):
            buildPayloads(inputs=[item])

    def test_11_invalid_review_status_fails_fast(self):
        item = approvedInput()
        item["reviewStatus"] = "PUBLISHED"
        with self.assertRaises(ValueError):
            buildPayloads(inputs=[item])

    def test_12_extra_field_is_forbidden_on_dto(self):
        item = approvedInput()
        item["extra"] = "nope"
        with self.assertRaises(ValidationError):
            RegulationApplicabilityInputV13(**item)

    def test_13_company_id_string_is_rejected(self):
        item = approvedInput()
        item["companyId"] = "A_GROUP"
        with self.assertRaises(ValidationError):
            RegulationApplicabilityInputV13(**item)

    def test_14_company_id_numeric_string_is_rejected(self):
        item = approvedInput()
        item["companyId"] = "1001"
        with self.assertRaises(ValidationError):
            RegulationApplicabilityInputV13(**item)

    def test_15_company_id_zero_is_rejected(self):
        item = approvedInput()
        item["companyId"] = 0
        with self.assertRaises(ValidationError):
            RegulationApplicabilityInputV13(**item)


class PhaseC31MappingExpansionTest(unittest.TestCase):
    def test_13_approved_input_and_mapping_create_payload(self):
        self.assertEqual(len(buildPayloads()), 1)

    def test_14_draft_input_is_excluded(self):
        item = approvedInput()
        item["reviewStatus"] = "DRAFT"
        self.assertEqual(buildPayloads(inputs=[item]), [])

    def test_15_reviewed_input_is_excluded(self):
        item = approvedInput()
        item["reviewStatus"] = "REVIEWED"
        self.assertEqual(buildPayloads(inputs=[item]), [])

    def test_16_draft_mapping_is_excluded(self):
        mapping = approvedMapping()
        mapping["reviewStatus"] = "DRAFT"
        self.assertEqual(buildPayloads(mappings=[mapping]), [])

    def test_17_inactive_mapping_is_excluded(self):
        mapping = approvedMapping()
        mapping["activeYn"] = False
        self.assertEqual(buildPayloads(mappings=[mapping]), [])

    def test_18_omitted_active_mapping_is_excluded(self):
        mapping = approvedMapping()
        del mapping["activeYn"]
        self.assertEqual(buildPayloads(mappings=[mapping]), [])

    def test_18_one_regime_expands_to_multiple_sub_issues(self):
        payloads = buildPayloads(mappings=[
            approvedMapping(subIssueCode=CSRD_SUB),
            approvedMapping(subIssueCode="G_RISK__ESG_RISK_MANAGEMENT"),
        ])
        self.assertEqual([item["subIssueCode"] for item in payloads], [
            CSRD_SUB,
            "G_RISK__ESG_RISK_MANAGEMENT",
        ])

    def test_19_multiple_regimes_expand_payloads(self):
        payloads = buildPayloads(
            inputs=[
                approvedInput(regime="CSRD", companyId=1001),
                approvedInput(regime="CBAM", companyId=1001),
            ],
            mappings=[
                approvedMapping(regime="CSRD", subIssueCode=CSRD_SUB),
                approvedMapping(regime="CBAM", subIssueCode=CBAM_SUB),
            ],
        )
        regimes = [item["screeningTrace"][0]["rawInputs"]["regime"] for item in payloads]
        self.assertEqual(regimes, ["CBAM", "CSRD"])

    def test_20_payload_preserves_sub_issue_code(self):
        self.assertEqual(buildPayloads()[0]["subIssueCode"], CSRD_SUB)

    def test_21_trace_raw_inputs_preserve_regime_and_applicability(self):
        raw = buildPayloads()[0]["screeningTrace"][0]["rawInputs"]
        self.assertEqual(raw["regime"], "CSRD")
        self.assertEqual(raw["applicability"], "DIRECT_MANDATORY")
        self.assertEqual(raw["inputMethod"], "MANUAL")
        self.assertEqual(raw["sourceDocumentRef"], "board-minutes-1")

    def test_22_deterministic_sort(self):
        inputs = [
            approvedInput(regime="DPP", companyId=2002, reportingYear=2027),
            approvedInput(regime="CSRD", companyId=1001, reportingYear=2026),
            approvedInput(regime="CBAM", companyId=1001, reportingYear=2026),
        ]
        mappings = [
            approvedMapping(regime="DPP", subIssueCode=DPP_SUB),
            approvedMapping(regime="CSRD", subIssueCode=CSRD_SUB),
            approvedMapping(regime="CBAM", subIssueCode=CBAM_SUB),
        ]
        payloads = buildPayloads(inputs=inputs, mappings=mappings)
        keys = [
            (
                item["screeningTrace"][0]["rawInputs"]["companyId"],
                item["screeningTrace"][0]["rawInputs"]["reportingYear"],
                item["screeningTrace"][0]["rawInputs"]["regime"],
                item["subIssueCode"],
            )
            for item in payloads
        ]
        self.assertEqual(keys, sorted(keys))


class PhaseC31DuplicateAndGuardTest(unittest.TestCase):
    def test_23_duplicate_approved_input_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(inputs=[approvedInput(), approvedInput()])

    def test_24_duplicate_regime_sub_issue_mapping_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(mappings=[approvedMapping(), approvedMapping()])

    def test_25_approved_input_without_mapping_returns_empty(self):
        self.assertEqual(buildPayloads(mappings=[approvedMapping(regime="CBAM", subIssueCode=CBAM_SUB)]), [])

    def test_26_empty_input_returns_empty(self):
        self.assertEqual(buildPayloads(inputs=[]), [])

    def test_27_empty_mapping_returns_empty(self):
        self.assertEqual(buildPayloads(mappings=[]), [])

    def test_28_unknown_mapping_regime_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(mappings=[approvedMapping(regime="ISSB")])

    def test_29_empty_sub_issue_code_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(mappings=[approvedMapping(subIssueCode="")])

    def test_30_unknown_sub_issue_code_fails_fast(self):
        with self.assertRaises(ValueError):
            buildPayloads(mappings=[approvedMapping(subIssueCode="NO_SUCH_SUB_ISSUE")])

    def test_31_dmascoring_has_no_duplicate_regulation_calculator(self):
        source = Path(ROOT, "src/utils/dmascoring.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"def step2CalcRegulation\(", source)), 1)

    def test_32_dmarepository_has_no_duplicate_regulation_calculator(self):
        # Phase C3.1.1 intentionally adds the regulation Shadow readers / serializer /
        # writer to dmarepository.py, so the original "no diff" guard no longer holds.
        # The invariant that must still hold (foundation §1.3): the repository never
        # re-implements the regulation calculator — rule-card scoring stays in
        # dmascoring.step2CalcRegulation and is reused via the orchestrator builder.
        source = Path(ROOT, "src/utils/dmarepository.py").read_text(encoding="utf-8")
        self.assertNotIn("def step2CalcRegulation", source)
        self.assertNotIn("step2CalcRegulation(", source)

    def test_33_summary_rank_externalmax_not_in_regulation_builder(self):
        source = inspect.getsource(orchestrator.step2BuildRegulationScreeningPayloads)
        for banned in (
            "ESG_DMA_SCORE_SUMMARY",
            "recalcStage(",
            "upsertStage(",
            "recalcFinal(",
            "updateRanks(",
            "externalMax",
        ):
            self.assertNotIn(banned, source)

    def test_34_manifest_has_no_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "backend/src/resources/dma/v1_3_mvp/manifest.json"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_35_screening_policy_has_no_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "backend/src/resources/dma/v1_3_mvp/screening_policy.json"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_36_mapping_seed_sub_issues_exist_in_master(self):
        for code in (CSRD_SUB, CBAM_SUB, DPP_SUB):
            self.assertIn(code, subissueMaster)

    def test_37_regulation_remains_media_external_source_type(self):
        payload = buildPayloads()[0]
        self.assertEqual(payload["sourceChannel"], "media_external")
        raw = payload["screeningTrace"][0]["rawInputs"]
        self.assertEqual(raw["sourceStep"], "media_external")
        self.assertEqual(raw["sourceType"], "regulation")

    def test_38_regime_and_applicability_are_not_hardcoded_in_orchestrator(self):
        source = Path(ROOT, "src/services/materialities/orchestrator.py").read_text(encoding="utf-8")
        self.assertNotIn("REGULATION_REGIMES", source)
        self.assertNotIn("REGULATION_APPLICABILITIES", source)

    def test_39_runtime_must_not_call_regulation_screening_directly(self):
        sourceRoot = Path(ROOT, "src")
        offenders = []
        for path in sourceRoot.rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if relative == "src/services/materialities/orchestrator.py":
                continue
            source = path.read_text(encoding="utf-8")
            if 'step2RunScreening("regulation"' in source or "step2RunScreening('regulation'" in source:
                offenders.append(relative)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
