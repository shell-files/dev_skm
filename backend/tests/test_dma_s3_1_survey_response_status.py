"""
S3.1 Survey Response Status — Test Suite
"""
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_form(form_id=1, survey_status="READY", master_sheet_id="SHEET1"):
    return {
        "id": form_id,
        "survey_status": survey_status,
        "master_sheet_id": master_sheet_id,
    }


def _make_conn(response_rows=None):
    conn = MagicMock()
    conn.autocommit = True
    cur = MagicMock()
    cur.fetchall.return_value = response_rows or []
    cursor_ctx = MagicMock()
    cursor_ctx.__enter__ = MagicMock(return_value=cur)
    cursor_ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor_ctx
    return conn, cur


# ---------------------------------------------------------------------------
# Import targets under test
# ---------------------------------------------------------------------------

from src.services.surveys.statusservice import (
    getSurveyResponseStatus,
    saveSurveyResponseTargets,
    _validateRunId,
    _validateTargets,
    _buildGroups,
    _RESPONSE_COUNT_SQL,
)
from src.utils.dmasurveytargetrepository import (
    SURVEY_TARGET_GROUPS,
    upsertTargetsTx,
)
from src.models.dmasurveyresponsestatus import (
    SurveyResponseStatusDto,
    SurveyGroupStatusDto,
    SurveyTotalsDto,
)


# ===========================================================================
# TestValidators
# ===========================================================================

class TestValidators(unittest.TestCase):

    def test_01_validate_run_id_rejects_zero(self):
        with self.assertRaises(ValueError):
            _validateRunId(0)

    def test_02_validate_run_id_rejects_negative(self):
        with self.assertRaises(ValueError):
            _validateRunId(-1)

    def test_03_validate_run_id_rejects_bool(self):
        with self.assertRaises(ValueError):
            _validateRunId(True)

    def test_04_validate_run_id_accepts_positive_int(self):
        _validateRunId(1)  # no exception

    def test_05_validate_targets_rejects_negative(self):
        with self.assertRaises(ValueError):
            _validateTargets({"employee": -1, "management": 10, "external": 5})

    def test_06_validate_targets_rejects_bool(self):
        with self.assertRaises(ValueError):
            _validateTargets({"employee": True, "management": 10, "external": 5})

    def test_07_validate_targets_rejects_unknown_group(self):
        with self.assertRaises(ValueError):
            _validateTargets({"employee": 10, "unknown_group": 5})

    def test_08_validate_targets_accepts_zero(self):
        _validateTargets({"employee": 0, "management": 0, "external": 0})  # no exception

    def test_09_validate_targets_accepts_partial(self):
        _validateTargets({"employee": 100})  # partial dict ok


# ===========================================================================
# TestBuildGroups
# ===========================================================================

class TestBuildGroups(unittest.TestCase):

    def test_10_response_rate_calculation(self):
        targets = {"employee": 150, "management": 20, "external": 80}
        counts = {"employee": 30, "management": 8, "external": 12}
        groups = _buildGroups(targets, counts)
        self.assertAlmostEqual(groups["employee"].responseRate, round(30 / 150, 4))
        self.assertAlmostEqual(groups["management"].responseRate, round(8 / 20, 4))
        self.assertAlmostEqual(groups["external"].responseRate, round(12 / 80, 4))

    def test_11_target_count_zero_response_rate_zero(self):
        targets = {"employee": 0, "management": 0, "external": 0}
        counts = {"employee": 0, "management": 0, "external": 0}
        groups = _buildGroups(targets, counts)
        self.assertEqual(groups["employee"].responseRate, 0.0)
        self.assertEqual(groups["management"].responseRate, 0.0)
        self.assertEqual(groups["external"].responseRate, 0.0)

    def test_12_missing_target_defaults_to_zero(self):
        # groups not in targets default to 0
        groups = _buildGroups({}, {})
        for g in SURVEY_TARGET_GROUPS:
            self.assertEqual(groups[g].targetCount, 0)

    def test_13_labels_are_korean(self):
        groups = _buildGroups({}, {})
        self.assertEqual(groups["employee"].label, "임직원")
        self.assertEqual(groups["management"].label, "경영진")
        self.assertEqual(groups["external"].label, "외부이해관계자")


# ===========================================================================
# TestGetSurveyResponseStatus
# ===========================================================================

class TestGetSurveyResponseStatus(unittest.TestCase):

    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_14_no_form_returns_zero_counts_no_db(self, mock_form, mock_targets):
        mock_form.return_value = None
        mock_targets.return_value = {"employee": 150, "management": 20, "external": 80}

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.runId, 47)
        self.assertIsNone(result.surveyFormId)
        self.assertIsNone(result.surveyStatus)
        self.assertEqual(result.groups["employee"].responseCount, 0)
        self.assertEqual(result.groups["management"].responseCount, 0)
        self.assertEqual(result.groups["external"].responseCount, 0)
        self.assertEqual(result.totals.responseCount, 0)

    @patch("src.services.surveys.statusservice.getConn")
    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_15_ready_form_returns_form_id_and_status(self, mock_form, mock_targets, mock_conn):
        mock_form.return_value = _make_form(form_id=5, survey_status="READY")
        mock_targets.return_value = {"employee": 100, "management": 10, "external": 50}
        conn, cur = _make_conn([])
        mock_conn.return_value = conn

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.surveyFormId, 5)
        self.assertEqual(result.surveyStatus, "READY")

    @patch("src.services.surveys.statusservice.getConn")
    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_16_response_count_from_db_rows(self, mock_form, mock_targets, mock_conn):
        mock_form.return_value = _make_form(form_id=1)
        mock_targets.return_value = {"employee": 150, "management": 20, "external": 80}
        db_rows = [
            {"respondent_group": "employee", "response_count": 32},
            {"respondent_group": "management", "response_count": 8},
            {"respondent_group": "external", "response_count": 13},
        ]
        conn, cur = _make_conn(db_rows)
        mock_conn.return_value = conn

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.groups["employee"].responseCount, 32)
        self.assertEqual(result.groups["management"].responseCount, 8)
        self.assertEqual(result.groups["external"].responseCount, 13)

    @patch("src.services.surveys.statusservice.getConn")
    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_17_totals_aggregates_all_groups(self, mock_form, mock_targets, mock_conn):
        mock_form.return_value = _make_form(form_id=1)
        mock_targets.return_value = {"employee": 150, "management": 20, "external": 80}
        db_rows = [
            {"respondent_group": "employee", "response_count": 30},
            {"respondent_group": "management", "response_count": 8},
            {"respondent_group": "external", "response_count": 12},
        ]
        conn, _ = _make_conn(db_rows)
        mock_conn.return_value = conn

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.totals.targetCount, 250)
        self.assertEqual(result.totals.responseCount, 50)
        self.assertAlmostEqual(result.totals.responseRate, round(50 / 250, 4))

    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_18_no_form_totals_target_sum_no_response(self, mock_form, mock_targets):
        mock_form.return_value = None
        mock_targets.return_value = {"employee": 150, "management": 20, "external": 80}

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.totals.targetCount, 250)
        self.assertEqual(result.totals.responseCount, 0)
        self.assertEqual(result.totals.responseRate, 0.0)

    def test_19_invalid_run_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            getSurveyResponseStatus(0)


# ===========================================================================
# TestDistinctSourceKey
# ===========================================================================

class TestDistinctSourceKey(unittest.TestCase):

    def test_20_response_count_sql_uses_distinct(self):
        self.assertIn("DISTINCT", _RESPONSE_COUNT_SQL)
        self.assertIn("source_response_key", _RESPONSE_COUNT_SQL)

    @patch("src.services.surveys.statusservice.getConn")
    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_21_top5_5_rows_count_as_one_respondent(self, mock_form, mock_targets, mock_conn):
        """DB returns response_count=1 when 5 rows share the same source_response_key."""
        mock_form.return_value = _make_form(form_id=1)
        mock_targets.return_value = {"employee": 10, "management": 10, "external": 10}
        # DB correctly deduplicates via DISTINCT and returns 1
        db_rows = [{"respondent_group": "employee", "response_count": 1}]
        conn, _ = _make_conn(db_rows)
        mock_conn.return_value = conn

        result = getSurveyResponseStatus(47)

        self.assertEqual(result.groups["employee"].responseCount, 1)

    @patch("src.services.surveys.statusservice.getConn")
    @patch("src.services.surveys.statusservice.getTargetsByRunId")
    @patch("src.services.surveys.statusservice.getSurveyFormByRunId")
    def test_22_query_passes_run_id_and_form_id_to_db(self, mock_form, mock_targets, mock_conn):
        mock_form.return_value = _make_form(form_id=99)
        mock_targets.return_value = {"employee": 10, "management": 10, "external": 10}
        conn, cur = _make_conn([])
        mock_conn.return_value = conn

        getSurveyResponseStatus(47)

        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        self.assertEqual(args[1], (47, 99))


# ===========================================================================
# TestSaveSurveyResponseTargets
# ===========================================================================

class TestSaveSurveyResponseTargets(unittest.TestCase):

    @patch("src.services.surveys.statusservice.getSurveyResponseStatus")
    @patch("src.services.surveys.statusservice.upsertTargetsTx")
    @patch("src.services.surveys.statusservice.getConn")
    def test_23_save_calls_upsert_and_returns_status(self, mock_conn, mock_upsert, mock_status):
        conn = MagicMock()
        conn.autocommit = True
        mock_conn.return_value = conn
        expected = MagicMock(spec=SurveyResponseStatusDto)
        mock_status.return_value = expected

        targets = {"employee": 150, "management": 20, "external": 80}
        result = saveSurveyResponseTargets(47, targets)

        mock_upsert.assert_called_once_with(conn, 47, targets)
        conn.commit.assert_called_once()
        self.assertIs(result, expected)

    @patch("src.services.surveys.statusservice.getConn")
    def test_24_negative_target_rejected_before_db(self, mock_conn):
        with self.assertRaises(ValueError):
            saveSurveyResponseTargets(47, {"employee": -5, "management": 10, "external": 10})
        mock_conn.assert_not_called()

    @patch("src.services.surveys.statusservice.getConn")
    def test_25_bool_target_rejected_before_db(self, mock_conn):
        with self.assertRaises(ValueError):
            saveSurveyResponseTargets(47, {"employee": True, "management": 10, "external": 10})
        mock_conn.assert_not_called()

    @patch("src.services.surveys.statusservice.getSurveyResponseStatus")
    @patch("src.services.surveys.statusservice.upsertTargetsTx")
    @patch("src.services.surveys.statusservice.getConn")
    def test_26_rollback_on_upsert_failure(self, mock_conn, mock_upsert, mock_status):
        conn = MagicMock()
        conn.autocommit = True
        mock_conn.return_value = conn
        mock_upsert.side_effect = RuntimeError("DB write failed")

        with self.assertRaises(RuntimeError):
            saveSurveyResponseTargets(47, {"employee": 10, "management": 5, "external": 5})

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    @patch("src.services.surveys.statusservice.getConn")
    def test_27_conn_closed_even_on_failure(self, mock_conn):
        conn = MagicMock()
        conn.autocommit = True
        conn.cursor.return_value.__enter__ = MagicMock(side_effect=RuntimeError("crash"))
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = conn

        with self.assertRaises(Exception):
            saveSurveyResponseTargets(47, {"employee": 10, "management": 5, "external": 5})

        conn.close.assert_called_once()

    @patch("src.services.surveys.statusservice.getSurveyResponseStatus")
    @patch("src.services.surveys.statusservice.upsertTargetsTx")
    @patch("src.services.surveys.statusservice.getConn")
    def test_28_missing_groups_not_sent_to_upsert(self, mock_conn, mock_upsert, mock_status):
        conn = MagicMock()
        conn.autocommit = True
        mock_conn.return_value = conn
        mock_status.return_value = MagicMock()

        # Only employee provided — management/external not included
        saveSurveyResponseTargets(47, {"employee": 100})

        mock_upsert.assert_called_once_with(conn, 47, {"employee": 100})


# ===========================================================================
# TestUpsertTargetsTx
# ===========================================================================

class TestUpsertTargetsTx(unittest.TestCase):

    def test_29_upsert_calls_execute_for_each_group_present(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        upsertTargetsTx(conn, 47, {"employee": 100, "management": 20, "external": 50})

        self.assertEqual(cur.execute.call_count, 3)

    def test_30_upsert_skips_groups_not_in_targets(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        upsertTargetsTx(conn, 47, {"employee": 100})

        self.assertEqual(cur.execute.call_count, 1)

    def test_31_upsert_passes_correct_params(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        upsertTargetsTx(conn, 47, {"employee": 150})

        args = cur.execute.call_args[0]
        self.assertEqual(args[1], (47, "employee", 150))


if __name__ == "__main__":
    unittest.main()
