"""
DMA v1.3 Phase C3.3 KIS CAPABILITY_PENDING contract tests.

Verifies:
  A. Policy / Manifest static contract (screening_policy.kis, manifest.kisFinancialResilience)
  B. step2GetKisState pure trace contract
  C. Static non-wiring guard (orchestrator, repository, service, externalMax, API/Frontend/SQL)

No live DB, Redis, Kafka, Docker, external API, KIS score calculation,
KIS DB table, KIS reader, KIS TX writer, or KIS service hook is exercised.
"""

import copy
import inspect
import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path


_DUMMY_ENV = {
    "host_ip": "127.0.0.1",
    "domain": "test",
    "skm_domain": "test",
    "file_dir": "/tmp",
    "gemini_api_key": "test",
    "gemini_model": "test",
    "kafka_server": "test",
    "kafka_topic": "test",
    "mail_username": "test",
    "mail_password": "test",
    "mail_from": "test@test",
    "access_token_expire_minutes": "1",
    "refresh_token_expire_days": "1",
    "invite_token_expire_days": "1",
    "redis_host": "test",
    "redis_port": "6379",
    "redis_db1": "0",
    "redis_db2": "1",
    "redis_db3": "2",
    "service_key": "test",
    "maria_db_user": "test",
    "maria_db_password": "test",
    "maria_db_host": "test",
    "maria_db_database": "test",
    "maria_db_port": "3306",
    "maria_db_key": "test",
    "cookie_key": "test",
    "APPS_SCRIPT_URL": "test",
    "pg_db_host": "test",
    "pg_db_port": "5432",
    "pg_db_database": "test",
    "pg_db_user": "test",
    "pg_db_password": "test",
    "ollama_url": "http://test",
}
for _key, _value in _DUMMY_ENV.items():
    os.environ.setdefault(_key, _value)

if "mariadb" not in sys.modules:
    _mariadb = types.ModuleType("mariadb")
    _mariadb.Error = Exception
    _mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = _mariadb

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import src.utils.dmaruleregistry as reg  # noqa: E402
from src.utils import dmascoring as sc  # noqa: E402


def _resetPolicies():
    reg.resetDmaRulesForTest()


# =========================================================
# 6.1  Policy / Manifest
# =========================================================

class KisCapabilityPolicyManifestTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    # #01 screening_policy.kis 존재
    def test_01_kis_exists_in_screening_policy(self):
        policy = reg.getPolicy("screening_policy")
        self.assertIn("kis", policy)

    # #02 capability = DATA_EXPORT_REQUIRED
    def test_02_capability_data_export_required(self):
        policy = reg.getPolicy("screening_policy")
        self.assertEqual(policy["kis"]["capability"], "DATA_EXPORT_REQUIRED")

    # #03 reason = GRID_THRESHOLDS_REQUIRED
    def test_03_reason_grid_thresholds_required(self):
        policy = reg.getPolicy("screening_policy")
        self.assertEqual(policy["kis"]["reason"], "GRID_THRESHOLDS_REQUIRED")

    # #04 creditRatingPredictionAllowedYn = false
    def test_04_credit_rating_prediction_not_allowed(self):
        policy = reg.getPolicy("screening_policy")
        self.assertIs(policy["kis"]["creditRatingPredictionAllowedYn"], False)

    # #05 officialCreditRatingLabelAllowedYn = false
    def test_05_official_credit_rating_label_not_allowed(self):
        policy = reg.getPolicy("screening_policy")
        self.assertIs(policy["kis"]["officialCreditRatingLabelAllowedYn"], False)

    # #06 manifest kisFinancialResilience = DATA_EXPORT_REQUIRED
    def test_06_manifest_kis_financial_resilience_data_export_required(self):
        manifest = reg.getManifest()
        self.assertEqual(manifest["capabilities"]["kisFinancialResilience"], "DATA_EXPORT_REQUIRED")

    # #07 policy capability == manifest capability
    def test_07_policy_capability_equals_manifest_capability(self):
        policy = reg.getPolicy("screening_policy")
        manifest = reg.getManifest()
        self.assertEqual(
            policy["kis"]["capability"],
            manifest["capabilities"]["kisFinancialResilience"],
        )

    # #08 validateKisScreeningPolicy baseline PASS
    def test_08_validate_kis_screening_policy_baseline_pass(self):
        policy = reg.getPolicy("screening_policy")
        manifest = reg.getManifest()
        reg.validateKisScreeningPolicy(policy, manifest)

    # #09 kis missing → Validation Error
    def test_09_kis_missing_raises_validation_error(self):
        policy = copy.deepcopy(reg.getPolicy("screening_policy"))
        manifest = reg.getManifest()
        del policy["kis"]
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)

    # #10 capability mismatch → Validation Error
    def test_10_capability_mismatch_raises_validation_error(self):
        policy = copy.deepcopy(reg.getPolicy("screening_policy"))
        manifest = reg.getManifest()
        policy["kis"]["capability"] = "READY"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)

    # #11 reason mismatch → Validation Error
    def test_11_reason_mismatch_raises_validation_error(self):
        policy = copy.deepcopy(reg.getPolicy("screening_policy"))
        manifest = reg.getManifest()
        policy["kis"]["reason"] = "WRONG_REASON"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)

    # #12 creditRatingPredictionAllowedYn true → Validation Error
    def test_12_credit_rating_prediction_true_raises_validation_error(self):
        policy = copy.deepcopy(reg.getPolicy("screening_policy"))
        manifest = reg.getManifest()
        policy["kis"]["creditRatingPredictionAllowedYn"] = True
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)

    # #13 officialCreditRatingLabelAllowedYn true → Validation Error
    def test_13_official_credit_rating_label_true_raises_validation_error(self):
        policy = copy.deepcopy(reg.getPolicy("screening_policy"))
        manifest = reg.getManifest()
        policy["kis"]["officialCreditRatingLabelAllowedYn"] = True
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)

    # #14 manifest capability mismatch → Validation Error
    def test_14_manifest_capability_mismatch_raises_validation_error(self):
        policy = reg.getPolicy("screening_policy")
        manifest = copy.deepcopy(reg.getManifest())
        manifest["capabilities"]["kisFinancialResilience"] = "READY"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKisScreeningPolicy(policy, manifest)


# =========================================================
# 6.2  Pure Trace
# =========================================================

class KisCapabilityTraceTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()
        policy = reg.getPolicy("screening_policy")
        self.trace = sc.step2GetKisState(policy)

    # #15 step2GetKisState() channel
    def test_15_channel_kis_financial_resilience(self):
        self.assertEqual(self.trace.channel, "kis_financial_resilience")

    # #16 scorePurpose = PRESURVEY_SCREENING
    def test_16_score_purpose_presurvey_screening(self):
        self.assertEqual(self.trace.scorePurpose.value, "PRESURVEY_SCREENING")

    # #17 impactSignal is None
    def test_17_impact_signal_is_none(self):
        self.assertIsNone(self.trace.impactSignal)

    # #18 financialSignal is None
    def test_18_financial_signal_is_none(self):
        self.assertIsNone(self.trace.financialSignal)

    # #19 status = CAPABILITY_PENDING
    def test_19_status_capability_pending(self):
        self.assertEqual(self.trace.status, "CAPABILITY_PENDING")

    # #20 capability = DATA_EXPORT_REQUIRED
    def test_20_capability_data_export_required(self):
        self.assertEqual(self.trace.capability, "DATA_EXPORT_REQUIRED")

    # #21 raw reason
    def test_21_raw_reason_grid_thresholds_required(self):
        self.assertEqual(self.trace.rawInputs["reason"], "GRID_THRESHOLDS_REQUIRED")

    # #22 raw creditRatingPredictionAllowedYn false
    def test_22_raw_credit_rating_prediction_false(self):
        self.assertIs(self.trace.rawInputs["creditRatingPredictionAllowedYn"], False)

    # #23 raw officialCreditRatingLabelAllowedYn false
    def test_23_raw_official_credit_rating_label_false(self):
        self.assertIs(self.trace.rawInputs["officialCreditRatingLabelAllowedYn"], False)


# =========================================================
# 6.3  Static Non-Wiring Guard
# =========================================================

class KisCapabilityNonWiringGuardTest(unittest.TestCase):
    def _src(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    # #24 orchestrator에 step2RunScreening("kis") 없음
    def test_24_orchestrator_no_step2_run_screening_kis(self):
        src = self._src("src/services/materialities/orchestrator.py")
        self.assertNotIn('step2RunScreening("kis"', src)
        self.assertNotIn("step2RunScreening('kis'", src)

    # #25 orchestrator에 step2BuildKis 함수 없음
    def test_25_orchestrator_no_step2_build_kis_function(self):
        src = self._src("src/services/materialities/orchestrator.py")
        self.assertIsNone(re.search(r'step2BuildKis[A-Za-z]', src))

    # #26 dmarepository에 KIS namespace 없음
    def test_26_dmarepository_no_kis_namespace(self):
        src = self._src("src/utils/dmarepository.py")
        self.assertNotIn("KIS_V13_SHADOW", src)
        self.assertNotIn("kis_v13_shadow", src)

    # #27 dmarepository에 KIS reader 없음
    def test_27_dmarepository_no_kis_reader(self):
        src = self._src("src/utils/dmarepository.py")
        self.assertIsNone(re.search(r'listApproved[A-Za-z]*[Kk]is', src))
        self.assertIsNone(re.search(r'readKis[A-Za-z]', src))
        self.assertIsNone(re.search(r'getKis[A-Za-z]', src))

    # #28 dmarepository에 KIS TX writer 없음
    def test_28_dmarepository_no_kis_tx_writer(self):
        src = self._src("src/utils/dmarepository.py")
        self.assertIsNone(re.search(r'[Rr]eplaceKis[A-Za-z]', src))
        self.assertIsNone(re.search(r'step4[A-Za-z]*Kis[A-Za-z]', src))
        self.assertIsNone(re.search(r'[Ww]rite[A-Za-z]*[Kk]is', src))

    # #29 media service에 refreshKis 함수 없음
    def test_29_media_service_no_refresh_kis(self):
        src = self._src("src/services/medias/service.py")
        self.assertNotIn("refreshKis", src)
        self.assertIsNone(re.search(r'def.*[Kk]is[A-Za-z]*Shadow', src))

    # #30 media service에 KIS Hook 없음
    def test_30_media_service_no_kis_hook(self):
        src = self._src("src/services/medias/service.py")
        self.assertNotIn("KisHook", src)
        self.assertNotIn("kis_hook", src)
        self.assertIsNone(re.search(r'[Kk]is[A-Za-z]*Hook', src))

    # #31 Summary / Rank 신규 KIS 호출 없음
    def test_31_orchestrator_no_kis_state_call(self):
        src = self._src("src/services/materialities/orchestrator.py")
        self.assertNotIn("step2GetKisState", src)
        self.assertIsNone(re.search(r'kisState|kis_state', src))

    # #32 externalMax KIS 입력 없음
    def test_32_external_max_no_kis_input(self):
        src = self._src("src/services/materialities/orchestrator.py")
        if "step2CalcExternalMax" in src:
            idx = src.index("step2CalcExternalMax")
            context = src[max(0, idx - 800):idx + 300]
            self.assertNotIn("kisState", context)
            self.assertNotIn("kis_state", context)
            self.assertNotIn("step2GetKisState", context)

    # #33 SQL / DDL KIS Diff 없음
    def test_33_no_sql_ddl_kis_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "*.sql", "*.ddl"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    # #34 API / Frontend Diff 없음
    def test_34_no_api_frontend_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "backend/src/apis", "frontend"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # survey.py is intentionally modified in C4.0 — exclude it from guard
        # S5-B16: 벤치마킹/미디어 API 를 Redux(reportSlice.js)로 통일하면서 허용된 프론트 파일은 제외
        _S5B16_ALLOWED_FRONTEND = {
            "frontend/src/stores/reportSlice.js",
            "frontend/src/homes/reports/BenchMarking.jsx",
            "frontend/src/homes/reports/Media.jsx",
        }
        changed = [
            f for f in (result.stdout or "").strip().splitlines()
            if "survey.py" not in f and f not in _S5B16_ALLOWED_FRONTEND
        ]
        self.assertEqual(changed, [])


if __name__ == "__main__":
    unittest.main()
