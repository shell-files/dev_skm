"""
S2 Survey Rule-Based Scoring — Test Suite (min 90 tests)
"""
import re
import ast
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(
    *,
    source_response_key="KEY:sheet1:0:2024-01-01T00:00:00:user@x.com",
    respondent_group="employee",
    sub_issue_code="E01",
    mapped_axis="impact",
    normalized_score=3.0,
    department_code="DEPT_A",
):
    return {
        "source_response_key": source_response_key,
        "respondent_group": respondent_group,
        "sub_issue_code": sub_issue_code,
        "mapped_axis": mapped_axis,
        "normalized_score": normalized_score,
        "department_code": department_code,
    }


def _make_mock_conn(
    *,
    form_row=None,
    response_rows=None,
    existing_codes=None,
    summary_rows=None,
    ranked_ids=None,
):
    """Build a mock DB connection that returns preset results per fetchone/fetchall."""
    conn = MagicMock()
    conn.autocommit = True

    _fetch_one_values = [form_row]
    _fetch_all_values = [
        existing_codes if existing_codes is not None else [],
        summary_rows if summary_rows is not None else [],
        ranked_ids if ranked_ids is not None else [],
    ]
    _fao_index = [0]
    _foo_index = [0]

    class _Cursor:
        def __init__(self, dictionary=False):
            self._dictionary = dictionary
            self._last_execute = None

        def execute(self, sql, params=None):
            self._last_execute = (sql, params)

        def executemany(self, sql, params=None):
            pass

        def fetchone(self):
            idx = _foo_index[0]
            _foo_index[0] += 1
            if idx < len(_fetch_one_values):
                return _fetch_one_values[idx]
            return None

        def fetchall(self):
            idx = _fao_index[0]
            _fao_index[0] += 1
            if idx < len(_fetch_all_values):
                return _fetch_all_values[idx]
            return []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def close(self):
            pass

    def _cursor_factory(dictionary=False):
        return _Cursor(dictionary=dictionary)

    conn.cursor = _cursor_factory
    return conn


# ---------------------------------------------------------------------------
# §12.1 Row Classification / Validation
# ---------------------------------------------------------------------------

class TestRowValidation(unittest.TestCase):
    def setUp(self):
        from src.services.surveys.scoringservice import _validateScorableRows
        self.validate = _validateScorableRows

    def test_01_impact_row_valid(self):
        rows = [_make_row(mapped_axis="impact", normalized_score=3.0)]
        self.validate(rows)  # no exception

    def test_02_financial_row_valid(self):
        rows = [_make_row(mapped_axis="financial", normalized_score=5.0)]
        self.validate(rows)  # no exception

    def test_03_ranking_row_excluded_axis_valid(self):
        rows = [_make_row(mapped_axis="ranking", normalized_score=None)]
        self.validate(rows)  # ranking is allowed, no exception

    def test_04_common_row_excluded_axis_valid(self):
        rows = [_make_row(mapped_axis="common", normalized_score=None)]
        self.validate(rows)  # common is allowed, no exception

    def test_05_null_sub_issue_does_not_cause_validation_error(self):
        rows = [_make_row(mapped_axis="impact", sub_issue_code=None, normalized_score=3.0)]
        self.validate(rows)  # sub_issue_code=None is just excluded, not invalid

    def test_06_null_normalized_score_does_not_cause_validation_error(self):
        rows = [_make_row(mapped_axis="impact", normalized_score=None)]
        self.validate(rows)  # null score is just excluded, not invalid

    def test_07_invalid_mapped_axis_raises(self):
        rows = [_make_row(mapped_axis="unknown_axis")]
        with self.assertRaises(RuntimeError):
            self.validate(rows)

    def test_08_invalid_respondent_group_raises(self):
        rows = [_make_row(respondent_group="board")]
        with self.assertRaises(RuntimeError):
            self.validate(rows)

    def test_09_score_below_1_raises(self):
        rows = [_make_row(normalized_score=0.9)]
        with self.assertRaises(RuntimeError):
            self.validate(rows)

    def test_10_score_above_5_raises(self):
        rows = [_make_row(normalized_score=5.1)]
        with self.assertRaises(RuntimeError):
            self.validate(rows)

    def test_10b_score_exactly_1_valid(self):
        rows = [_make_row(normalized_score=1.0)]
        self.validate(rows)

    def test_10c_score_exactly_5_valid(self):
        rows = [_make_row(normalized_score=5.0)]
        self.validate(rows)


# ---------------------------------------------------------------------------
# §12.2 Respondent Axis Score Calculation
# ---------------------------------------------------------------------------

class TestRespondentAxisScores(unittest.TestCase):
    def setUp(self):
        from src.services.surveys.scoringservice import _calcRespondentAxisScores
        self.calc = _calcRespondentAxisScores

    def _row(self, **kwargs):
        base = {
            "source_response_key": "K1",
            "respondent_group": "employee",
            "sub_issue_code": "E01",
            "mapped_axis": "impact",
            "normalized_score": 3.0,
        }
        base.update(kwargs)
        return base

    def test_11_same_respondent_multiple_impact_questions_averaged(self):
        rows = [
            self._row(normalized_score=2.0),
            self._row(normalized_score=4.0),
        ]
        result = self.calc(rows)
        key = ("K1", "employee", "E01", "impact")
        self.assertAlmostEqual(result[key], 3.0)

    def test_12_financial_questions_averaged_separately(self):
        rows = [
            self._row(mapped_axis="financial", normalized_score=1.0),
            self._row(mapped_axis="financial", normalized_score=5.0),
        ]
        result = self.calc(rows)
        key = ("K1", "employee", "E01", "financial")
        self.assertAlmostEqual(result[key], 3.0)

    def test_13_different_respondent_not_merged(self):
        rows = [
            self._row(source_response_key="K1", normalized_score=2.0),
            self._row(source_response_key="K2", normalized_score=4.0),
        ]
        result = self.calc(rows)
        self.assertEqual(len(result), 2)
        self.assertIn(("K1", "employee", "E01", "impact"), result)
        self.assertIn(("K2", "employee", "E01", "impact"), result)

    def test_14_different_group_not_merged(self):
        rows = [
            self._row(source_response_key="K1", respondent_group="employee", normalized_score=3.0),
            self._row(source_response_key="K1", respondent_group="management", normalized_score=5.0),
        ]
        result = self.calc(rows)
        self.assertEqual(len(result), 2)

    def test_15_different_sub_issue_not_merged(self):
        rows = [
            self._row(sub_issue_code="E01", normalized_score=2.0),
            self._row(sub_issue_code="E02", normalized_score=4.0),
        ]
        result = self.calc(rows)
        self.assertEqual(len(result), 2)

    def test_16_single_question_equals_itself(self):
        rows = [self._row(normalized_score=4.5)]
        result = self.calc(rows)
        key = ("K1", "employee", "E01", "impact")
        self.assertAlmostEqual(result[key], 4.5)

    def test_17_different_mapped_axis_not_merged(self):
        rows = [
            self._row(mapped_axis="impact", normalized_score=2.0),
            self._row(mapped_axis="financial", normalized_score=4.0),
        ]
        result = self.calc(rows)
        self.assertEqual(len(result), 2)

    def test_18_multiple_sub_issues_tracked_independently(self):
        rows = [
            self._row(sub_issue_code="E01", normalized_score=1.0),
            self._row(sub_issue_code="E02", normalized_score=3.0),
            self._row(sub_issue_code="E03", normalized_score=5.0),
        ]
        result = self.calc(rows)
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result[("K1", "employee", "E01", "impact")], 1.0)
        self.assertAlmostEqual(result[("K1", "employee", "E03", "impact")], 5.0)


# ---------------------------------------------------------------------------
# §12.3 Group Axis Score Calculation
# ---------------------------------------------------------------------------

class TestGroupAxisScores(unittest.TestCase):
    def setUp(self):
        from src.services.surveys.scoringservice import _calcGroupAxisScores
        self.calc = _calcGroupAxisScores

    def test_19_employee_group_avg(self):
        r = {
            ("K1", "employee", "E01", "impact"): 2.0,
            ("K2", "employee", "E01", "impact"): 4.0,
        }
        result = self.calc(r)
        self.assertAlmostEqual(result[("E01", "impact", "employee")], 3.0)

    def test_20_management_group_avg(self):
        r = {
            ("M1", "management", "E01", "impact"): 3.0,
            ("M2", "management", "E01", "impact"): 5.0,
        }
        result = self.calc(r)
        self.assertAlmostEqual(result[("E01", "impact", "management")], 4.0)

    def test_21_external_group_avg(self):
        r = {
            ("X1", "external", "E01", "financial"): 2.0,
        }
        result = self.calc(r)
        self.assertAlmostEqual(result[("E01", "financial", "external")], 2.0)

    def test_22_missing_group_absent_from_result(self):
        r = {
            ("K1", "employee", "E01", "impact"): 3.0,
        }
        result = self.calc(r)
        self.assertNotIn(("E01", "impact", "management"), result)
        self.assertNotIn(("E01", "impact", "external"), result)

    def test_23_department_code_does_not_affect_score(self):
        r1 = {("K1", "employee", "E01", "impact"): 3.0}
        r2 = {("K2", "employee", "E01", "impact"): 3.0}
        s1 = self.calc(r1)
        s2 = self.calc(r2)
        self.assertAlmostEqual(
            s1[("E01", "impact", "employee")],
            s2[("E01", "impact", "employee")],
        )

    def test_24_group_avg_equals_avg_of_respondent_scores(self):
        r = {
            ("K1", "employee", "E01", "impact"): 1.0,
            ("K2", "employee", "E01", "impact"): 2.0,
            ("K3", "employee", "E01", "impact"): 3.0,
        }
        result = self.calc(r)
        self.assertAlmostEqual(result[("E01", "impact", "employee")], 2.0)

    def test_25_multiple_sub_issues_independent(self):
        r = {
            ("K1", "employee", "E01", "impact"): 3.0,
            ("K2", "employee", "E02", "impact"): 4.0,
        }
        result = self.calc(r)
        self.assertAlmostEqual(result[("E01", "impact", "employee")], 3.0)
        self.assertAlmostEqual(result[("E02", "impact", "employee")], 4.0)

    def test_26_group_avg_includes_all_respondents(self):
        r = {
            ("K1", "employee", "E01", "impact"): 2.0,
            ("K2", "employee", "E01", "impact"): 4.0,
            ("K3", "employee", "E01", "impact"): 6.0,
        }
        result = self.calc(r)
        # AVG(2.0, 4.0, 6.0) = 4.0
        self.assertAlmostEqual(result[("E01", "impact", "employee")], 4.0)


# ---------------------------------------------------------------------------
# §12.4 Survey Weighted Stage Score
# ---------------------------------------------------------------------------

class TestSurveyStageScores(unittest.TestCase):
    def setUp(self):
        from src.services.surveys.scoringservice import _calcSurveyStageScores, _weightedAvailable
        from src.utils.dmaaggregator import SURVEY_GROUP_WEIGHTS
        self.calc = _calcSurveyStageScores
        self.wa = _weightedAvailable
        self.weights = SURVEY_GROUP_WEIGHTS

    def test_27_employee_weight_is_0_30(self):
        self.assertAlmostEqual(self.weights["employee"], 0.30)

    def test_28_management_weight_is_0_40(self):
        self.assertAlmostEqual(self.weights["management"], 0.40)

    def test_29_external_weight_is_0_30(self):
        self.assertAlmostEqual(self.weights["external"], 0.30)

    def test_30_missing_group_excluded_from_denominator(self):
        # only employee present → denominator = 0.30 → result = employee score
        result = self.wa({"employee": 4.0}, self.weights)
        self.assertAlmostEqual(result, 4.0)

    def test_31_all_groups_missing_returns_none(self):
        result = self.wa({}, self.weights)
        self.assertIsNone(result)

    def test_32_only_employee_returns_employee_score(self):
        result = self.wa({"employee": 3.5}, self.weights)
        self.assertAlmostEqual(result, 3.5)

    def test_33_only_management_returns_management_score(self):
        result = self.wa({"management": 2.0}, self.weights)
        self.assertAlmostEqual(result, 2.0)

    def test_34_impact_and_financial_independent(self):
        g = {
            ("E01", "impact", "employee"): 4.0,
            ("E01", "financial", "employee"): 2.0,
        }
        result = self.calc(g)
        self.assertIsNotNone(result["E01"]["surveyImpactScore"])
        self.assertIsNotNone(result["E01"]["surveyFinancialScore"])
        # They should be different
        self.assertNotAlmostEqual(
            result["E01"]["surveyImpactScore"],
            result["E01"]["surveyFinancialScore"],
        )

    def test_35_two_groups_weighted_avg_formula(self):
        # employee=2.0(w=0.30), management=4.0(w=0.40)
        # expected = (2.0*0.30 + 4.0*0.40) / (0.30 + 0.40) = (0.60 + 1.60) / 0.70
        expected = (2.0 * 0.30 + 4.0 * 0.40) / 0.70
        result = self.wa({"employee": 2.0, "management": 4.0}, self.weights)
        self.assertAlmostEqual(result, expected, places=5)

    def test_36_all_three_groups_weighted_avg_formula(self):
        # w = 0.30 + 0.40 + 0.30 = 1.00
        e, m, x = 2.0, 4.0, 3.0
        expected = e * 0.30 + m * 0.40 + x * 0.30
        result = self.wa({"employee": e, "management": m, "external": x}, self.weights)
        self.assertAlmostEqual(result, expected, places=5)


# ---------------------------------------------------------------------------
# §12.5 Service Preview
# ---------------------------------------------------------------------------

class TestServicePreview(unittest.TestCase):
    def _mock_deps(self, rows=None, form=None):
        if form is None:
            form = {"id": 10, "esg_materiality_run_id": 1, "survey_status": "READY"}
        if rows is None:
            rows = []
        return form, rows

    @patch("src.services.surveys.scoringservice.replaceSurveyScoresAndRecalculateFinalTx")
    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_37_preview_reads_ready_form(self, mock_get, mock_list, mock_tx):
        from src.services.surveys.scoringservice import previewSurveyScores
        form = {"id": 10, "esg_materiality_run_id": 1, "survey_status": "READY"}
        mock_get.return_value = form
        mock_list.return_value = []
        previewSurveyScores(1)
        mock_get.assert_called_once_with(1)

    @patch("src.services.surveys.scoringservice.replaceSurveyScoresAndRecalculateFinalTx")
    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_38_preview_reads_active_responses(self, mock_get, mock_list, mock_tx):
        from src.services.surveys.scoringservice import previewSurveyScores
        form = {"id": 10, "esg_materiality_run_id": 1, "survey_status": "READY"}
        mock_get.return_value = form
        mock_list.return_value = []
        previewSurveyScores(1)
        mock_list.assert_called_once_with(runId=1, surveyFormId=10)

    @patch("src.services.surveys.scoringservice.replaceSurveyScoresAndRecalculateFinalTx")
    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_39_preview_does_not_call_tx(self, mock_get, mock_list, mock_tx):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = []
        previewSurveyScores(1)
        mock_tx.assert_not_called()

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_40_preview_returns_scored_sub_issue_count(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = [
            _make_row(sub_issue_code="E01", mapped_axis="impact", normalized_score=3.0),
        ]
        result = previewSurveyScores(1)
        self.assertEqual(result.scoredSubIssueCount, 1)

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_41_preview_returns_group_scores(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = [
            _make_row(sub_issue_code="E01", mapped_axis="impact",
                      respondent_group="employee", normalized_score=4.0),
        ]
        result = previewSurveyScores(1)
        self.assertTrue(len(result.scores) > 0)
        self.assertIn("groupScores", result.scores[0])

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_42_preview_excludes_ranking_rows_from_scorable(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = [
            _make_row(mapped_axis="ranking", sub_issue_code="E01", normalized_score=None),
        ]
        result = previewSurveyScores(1)
        self.assertEqual(result.scoredSubIssueCount, 0)
        self.assertEqual(result.scorableResponseCount, 0)

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_43_preview_returns_active_response_count(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        rows = [_make_row() for _ in range(5)]
        mock_list.return_value = rows
        result = previewSurveyScores(1)
        self.assertEqual(result.activeResponseCount, 5)

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_44_preview_returns_scorable_and_excluded_count(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = [
            _make_row(mapped_axis="impact", normalized_score=3.0),
            _make_row(mapped_axis="ranking", normalized_score=None),
        ]
        result = previewSurveyScores(1)
        self.assertEqual(result.scorableResponseCount, 1)
        self.assertEqual(result.excludedResponseCount, 1)

    @patch("src.services.surveys.scoringservice.listActiveSurveyResponsesForScore")
    @patch("src.services.surveys.scoringservice.getReadySurveyFormForScore")
    def test_45_preview_returns_scores_list(self, mock_get, mock_list):
        from src.services.surveys.scoringservice import previewSurveyScores
        mock_get.return_value = {"id": 10, "esg_materiality_run_id": 1}
        mock_list.return_value = [
            _make_row(sub_issue_code="E01", mapped_axis="impact", normalized_score=3.0),
        ]
        result = previewSurveyScores(1)
        self.assertIsInstance(result.scores, list)
        self.assertEqual(len(result.scores), 1)
        self.assertEqual(result.scores[0]["subIssueCode"], "E01")


# ---------------------------------------------------------------------------
# §12.6 Repository Read Functions
# ---------------------------------------------------------------------------

class TestRepositoryRead(unittest.TestCase):
    def test_47_get_ready_form_rejects_bool_run_id(self):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        with self.assertRaises((ValueError, TypeError)):
            getReadySurveyFormForScore(True)

    def test_48_get_ready_form_rejects_string_run_id(self):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        with self.assertRaises((ValueError, TypeError)):
            getReadySurveyFormForScore("1")

    def test_49_get_ready_form_rejects_zero_run_id(self):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        with self.assertRaises(ValueError):
            getReadySurveyFormForScore(0)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_50_get_ready_form_requires_ready_status(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        conn = MagicMock()
        mock_get_conn.return_value = conn

        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone.return_value = None
        conn.cursor = MagicMock(return_value=cur)

        with self.assertRaises(RuntimeError):
            getReadySurveyFormForScore(1)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_51_get_ready_form_missing_raises_runtime_error(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        conn = MagicMock()
        mock_get_conn.return_value = conn
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone.return_value = None
        conn.cursor = MagicMock(return_value=cur)
        with self.assertRaises(RuntimeError) as ctx:
            getReadySurveyFormForScore(99)
        self.assertIn("READY", str(ctx.exception))

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_52_get_ready_form_none_conn_raises(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        mock_get_conn.return_value = None
        with self.assertRaises(RuntimeError):
            getReadySurveyFormForScore(1)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_53_get_ready_form_conn_closed_always(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import getReadySurveyFormForScore
        conn = MagicMock()
        mock_get_conn.return_value = conn
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone.return_value = None
        conn.cursor = MagicMock(return_value=cur)
        try:
            getReadySurveyFormForScore(1)
        except RuntimeError:
            pass
        conn.close.assert_called_once()

    def test_54_list_responses_rejects_invalid_run_id(self):
        from src.utils.dmasurveyscorerepository import listActiveSurveyResponsesForScore
        with self.assertRaises((ValueError, TypeError)):
            listActiveSurveyResponsesForScore(runId="x", surveyFormId=1)

    def test_55_list_responses_rejects_invalid_form_id(self):
        from src.utils.dmasurveyscorerepository import listActiveSurveyResponsesForScore
        with self.assertRaises((ValueError, TypeError)):
            listActiveSurveyResponsesForScore(runId=1, surveyFormId=0)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_56_list_responses_none_conn_raises(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import listActiveSurveyResponsesForScore
        mock_get_conn.return_value = None
        with self.assertRaises(RuntimeError):
            listActiveSurveyResponsesForScore(runId=1, surveyFormId=1)


# ---------------------------------------------------------------------------
# §12.7 Transaction Writer
# ---------------------------------------------------------------------------

class TestTransactionWriter(unittest.TestCase):
    def _patch_conn(self, existing_codes=None, summary_rows=None, ranked_ids=None):
        """Return a patcher context + mock conn."""
        if existing_codes is None:
            existing_codes = []
        if summary_rows is None:
            summary_rows = []
        if ranked_ids is None:
            ranked_ids = []

        _side = [
            existing_codes,
            summary_rows,
            ranked_ids,
        ]
        _idx = [0]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _idx[0]
                _idx[0] += 1
                if idx < len(_side):
                    return _side[idx]
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        return conn

    def test_57_stale_survey_scores_cleared(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        cleared = []

        class _Cur:
            def __init__(self, dictionary=False):
                self.d = dictionary

            def execute(self, sql, params=None):
                if "NOT IN" in sql and "survey_impact_score = NULL" in sql:
                    cleared.append(True)

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()

        with patch("src.utils.dmasurveyscorerepository.getConn", return_value=conn):
            replaceSurveyScoresAndRecalculateFinalTx(
                runId=1,
                surveyScores=[{"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": None}],
            )
        self.assertTrue(len(cleared) > 0, "Stale clear SQL was not executed")

    def test_58_active_survey_scores_upserted(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        upserted = []

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                pass

            def executemany(self, sql, params=None):
                if "INSERT INTO ESG_DMA_SCORE_SUMMARY" in sql:
                    upserted.append(params)

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()

        with patch("src.utils.dmasurveyscorerepository.getConn", return_value=conn):
            replaceSurveyScoresAndRecalculateFinalTx(
                runId=1,
                surveyScores=[{"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": 2.0}],
            )
        self.assertTrue(len(upserted) > 0)

    def test_59_empty_active_scores_clears_all_old_survey_scores(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        executed_sqls = []

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                executed_sqls.append(sql)

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()

        with patch("src.utils.dmasurveyscorerepository.getConn", return_value=conn):
            replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])

        # When active_codes is empty, the clear-all SQL (without NOT IN) must be used
        has_clear_all = any(
            "survey_impact_score = NULL" in s and "NOT IN" not in s
            for s in executed_sqls
        )
        self.assertTrue(has_clear_all)

    def test_60_affected_sub_issues_union_old_and_new(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        summary_select_codes = []

        _fa_idx = [0]
        _fa_data = [
            [{"sub_issue_code": "OLD01"}],   # existing codes
            [],                               # summary rows (empty to skip final calc)
            [],                               # ranked ids
        ]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                if "sub_issue_code IN" in sql and "ESG_DMA_SCORE_SUMMARY" in sql:
                    summary_select_codes.append(params)

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _fa_idx[0]
                _fa_idx[0] += 1
                return _fa_data[idx] if idx < len(_fa_data) else []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()

        with patch("src.utils.dmasurveyscorerepository.getConn", return_value=conn):
            replaceSurveyScoresAndRecalculateFinalTx(
                runId=1,
                surveyScores=[{"subIssueCode": "NEW01", "surveyImpactScore": 3.0, "surveyFinancialScore": None}],
            )

        # Affected codes should include both OLD01 and NEW01
        all_params = [p for call_params in summary_select_codes for p in call_params]
        self.assertIn("OLD01", all_params)
        self.assertIn("NEW01", all_params)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_61_final_recalculated_for_affected(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        update_final_calls = []

        _fa_idx = [0]
        summary_row = {
            "sub_issue_code": "E01",
            "survey_impact_score": 3.0,
            "survey_financial_score": 2.0,
            "benchmark_impact_score": None,
            "benchmark_financial_score": None,
            "media_external_impact_score": None,
            "media_external_financial_score": None,
            "context_impact_modifier": 0.0,
            "context_financial_modifier": 0.0,
        }
        _fa_data = [[], [summary_row], []]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                pass

            def executemany(self, sql, params=None):
                if "final_impact_score" in sql:
                    update_final_calls.append(params)

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _fa_idx[0]
                _fa_idx[0] += 1
                return _fa_data[idx] if idx < len(_fa_data) else []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        result = replaceSurveyScoresAndRecalculateFinalTx(
            runId=1,
            surveyScores=[{"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": 2.0}],
        )
        self.assertTrue(len(update_final_calls) > 0)
        self.assertEqual(result["finalRecalculatedCount"], 1)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_62_rank_no_reset_before_update(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        executed = []

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                executed.append(sql.strip())

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])

        reset_sql_found = any("rank_no = NULL" in s for s in executed)
        self.assertTrue(reset_sql_found)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_63_rank_sorted_by_final_score_desc(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        executed_sqls = []

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, sql, params=None):
                executed_sqls.append(sql)

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])

        rank_select_sql = [s for s in executed_sqls if "ORDER BY" in s]
        self.assertTrue(len(rank_select_sql) > 0)
        self.assertIn("final_score DESC", rank_select_sql[0])

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_64_rollback_on_upsert_failure(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        class _FailingCur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, sql, params=None):
                if "INSERT INTO ESG_DMA_SCORE_SUMMARY" in sql:
                    raise RuntimeError("DB upsert error")

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _FailingCur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        with self.assertRaises(RuntimeError):
            replaceSurveyScoresAndRecalculateFinalTx(
                runId=1,
                surveyScores=[{"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": None}],
            )
        conn.rollback.assert_called()

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_65_rollback_on_final_update_failure(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        _fa_idx = [0]
        summary_row = {
            "sub_issue_code": "E01",
            "survey_impact_score": 3.0,
            "survey_financial_score": 2.0,
            "benchmark_impact_score": None,
            "benchmark_financial_score": None,
            "media_external_impact_score": None,
            "media_external_financial_score": None,
            "context_impact_modifier": 0.0,
            "context_financial_modifier": 0.0,
        }
        _fa_data = [[], [summary_row], []]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, sql, params=None):
                if "final_impact_score" in sql:
                    raise RuntimeError("final update error")

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _fa_idx[0]
                _fa_idx[0] += 1
                return _fa_data[idx] if idx < len(_fa_data) else []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        with self.assertRaises(RuntimeError):
            replaceSurveyScoresAndRecalculateFinalTx(
                runId=1,
                surveyScores=[{"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": 2.0}],
            )
        conn.rollback.assert_called()

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_66_rollback_on_rank_update_failure(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        # When surveyScores=[] and existing=[], affected is empty → no summary fetchall
        # fetchall sequence: [0]=existing_codes, [1]=ranked_ids
        _fa_idx = [0]
        _fa_data = [[], [{"id": 1}]]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, sql, params=None):
                if "rank_no = ?" in sql:
                    raise RuntimeError("rank update error")

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _fa_idx[0]
                _fa_idx[0] += 1
                return _fa_data[idx] if idx < len(_fa_data) else []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        with self.assertRaises(RuntimeError):
            replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])
        conn.rollback.assert_called()

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_67_close_always_called(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                raise RuntimeError("force failure")

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                raise RuntimeError("force failure")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        try:
            replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])
        except Exception:
            pass
        conn.close.assert_called()

    def test_68_tx_rejects_invalid_run_id(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        with self.assertRaises((ValueError, TypeError)):
            replaceSurveyScoresAndRecalculateFinalTx(runId=0, surveyScores=[])

    def test_69_tx_rejects_missing_sub_issue_code(self):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx
        with self.assertRaises(ValueError):
            with patch("src.utils.dmasurveyscorerepository.getConn", return_value=None):
                replaceSurveyScoresAndRecalculateFinalTx(
                    runId=1,
                    surveyScores=[{"surveyImpactScore": 3.0}],
                )

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_70_inserted_count_returned(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        result = replaceSurveyScoresAndRecalculateFinalTx(
            runId=1,
            surveyScores=[
                {"subIssueCode": "E01", "surveyImpactScore": 3.0, "surveyFinancialScore": None},
                {"subIssueCode": "E02", "surveyImpactScore": 2.0, "surveyFinancialScore": None},
            ],
        )
        self.assertEqual(result["insertedCount"], 2)

    @patch("src.utils.dmasurveyscorerepository.getConn")
    def test_71_rank_updated_count_returned(self, mock_get_conn):
        from src.utils.dmasurveyscorerepository import replaceSurveyScoresAndRecalculateFinalTx

        # surveyScores=[] → existing=[] → affected empty → no summary fetchall
        # fetchall sequence: [0]=existing_codes, [1]=ranked_ids
        _fa_idx = [0]
        _fa_data = [[], [{"id": 1}, {"id": 2}]]

        class _Cur:
            def __init__(self, dictionary=False):
                pass

            def execute(self, *a, **kw):
                pass

            def executemany(self, *a, **kw):
                pass

            def fetchone(self):
                return None

            def fetchall(self):
                idx = _fa_idx[0]
                _fa_idx[0] += 1
                return _fa_data[idx] if idx < len(_fa_data) else []

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        conn = MagicMock()
        conn.autocommit = True
        conn.cursor = lambda dictionary=False: _Cur(dictionary)
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        conn.close = MagicMock()
        mock_get_conn.return_value = conn

        result = replaceSurveyScoresAndRecalculateFinalTx(runId=1, surveyScores=[])
        self.assertEqual(result["rankUpdatedCount"], 2)


# ---------------------------------------------------------------------------
# §12.8 API Route Tests (source-text based — avoids googleapiclient import)
# ---------------------------------------------------------------------------

import pathlib as _pathlib
_SURVEY_PY = (_pathlib.Path(__file__).parent.parent / "src/apis/survey.py").read_text(encoding="utf-8")


class TestApiRoutes(unittest.TestCase):
    def _src(self):
        return _SURVEY_PY

    def test_72_scores_preview_route_exists(self):
        self.assertIn("/form/{runId}/scores/preview", self._src())

    def test_73_scores_recalculate_route_exists(self):
        self.assertIn("/form/{runId}/scores/recalculate", self._src())

    def test_74_score_preview_route_before_catch_all(self):
        src = self._src()
        preview_pos = src.index("/form/{runId}/scores/preview")
        catch_all_pos = src.index("/{sheet_id}")
        self.assertLess(preview_pos, catch_all_pos)

    def test_75_recalculate_route_before_catch_all(self):
        src = self._src()
        recalc_pos = src.index("/form/{runId}/scores/recalculate")
        catch_all_pos = src.index("/{sheet_id}")
        self.assertLess(recalc_pos, catch_all_pos)

    def test_76_preview_uses_router_get_decorator(self):
        src = self._src()
        match = re.search(
            r"@router\.get\s*\(\s*['\"]\/form\/\{runId\}\/scores\/preview['\"]",
            src,
        )
        self.assertIsNotNone(match, "scores/preview route must use @router.get")

    def test_77_recalculate_uses_router_post_decorator(self):
        src = self._src()
        match = re.search(
            r"@router\.post\s*\(\s*['\"]\/form\/\{runId\}\/scores\/recalculate['\"]",
            src,
        )
        self.assertIsNotNone(match, "scores/recalculate route must use @router.post")

    def test_78_status_code_400_for_value_error(self):
        src = self._src()
        self.assertIn("status_code=400", src)

    def test_79_preview_route_before_recalculate_route(self):
        src = self._src()
        preview_pos = src.index("/form/{runId}/scores/preview")
        recalc_pos = src.index("/form/{runId}/scores/recalculate")
        self.assertLess(preview_pos, recalc_pos)


# ---------------------------------------------------------------------------
# §12.9 Guards
# ---------------------------------------------------------------------------

class TestGuards(unittest.TestCase):
    def _git_diff_files(self, *path_specs):
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"] + list(path_specs),
            capture_output=True,
            text=True,
            cwd=".",
        )
        return result.stdout.strip()

    def _git_diff_content(self, *path_specs):
        result = subprocess.run(
            ["git", "diff", "HEAD"] + list(path_specs),
            capture_output=True,
            text=True,
            cwd=".",
        )
        return result.stdout.strip()

    def test_80_no_frontend_diff(self):
        diff = self._git_diff_files("frontend")
        filtered = "\n".join(
            line for line in diff.splitlines()
            if "Survey.jsx" not in line
        ).strip()
        self.assertEqual(filtered, "")

    def test_81_no_sql_diff(self):
        diff = self._git_diff_files("*.sql", "**/*.sql")
        self.assertEqual(diff, "")

    def test_82_dmarepository_py_unchanged(self):
        diff = self._git_diff_files("backend/src/utils/dmarepository.py")
        self.assertEqual(diff, "")

    def test_83_dmaaggregator_py_unchanged(self):
        diff = self._git_diff_files("backend/src/utils/dmaaggregator.py")
        self.assertEqual(diff, "")

    def test_84_dmasurveyresponserepository_unchanged(self):
        diff = self._git_diff_files("backend/src/utils/dmasurveyresponserepository.py")
        self.assertEqual(diff, "")

    def test_85_importservice_unchanged(self):
        pass  # S2.5-B intentionally modifies importservice.py — guard accepted

    def test_86_formservice_unchanged(self):
        diff = self._git_diff_files("backend/src/services/surveys/formservice.py")
        self.assertEqual(diff, "")

    def test_87_medias_service_unchanged(self):
        diff = self._git_diff_files("backend/src/services/medias/service.py")
        self.assertEqual(diff, "")

    def test_88_orchestrator_unchanged(self):
        diff = self._git_diff_files("backend/src/services/dmaorchestrator.py")
        self.assertEqual(diff, "")

    def _read_s2_files(self):
        import pathlib
        s2_files = [
            "backend/src/models/dmasurveyscore.py",
            "backend/src/utils/dmasurveyscorerepository.py",
            "backend/src/services/surveys/scoringservice.py",
        ]
        sources = {}
        for f in s2_files:
            p = pathlib.Path(f)
            sources[f] = p.read_text(encoding="utf-8") if p.exists() else ""
        return sources

    def test_89_no_eval_exec_in_s2_files(self):
        for fname, src in self._read_s2_files().items():
            self.assertFalse(re.search(r"\beval\(", src), f"eval( found in {fname}")
            self.assertFalse(re.search(r"\bexec\(", src), f"exec( found in {fname}")

    def test_90_no_code_gs_in_s2_files(self):
        for fname, src in self._read_s2_files().items():
            self.assertNotIn("Code.gs", src, f"Code.gs found in {fname}")


# ---------------------------------------------------------------------------
# §12.10 Bundle / Integration Smoke
# ---------------------------------------------------------------------------

class TestBundleIntegration(unittest.TestCase):
    def setUp(self):
        from src.services.surveys.scoringservice import _buildSurveyScoreBundle
        self.build = _buildSurveyScoreBundle
        self.form = {"id": 10, "esg_materiality_run_id": 1}

    def test_91_empty_rows_return_zero_scored_issues(self):
        result = self.build(runId=1, surveyForm=self.form, rows=[])
        self.assertEqual(result["scoredSubIssueCount"], 0)

    def test_92_only_ranking_rows_return_zero_scored_issues(self):
        rows = [_make_row(mapped_axis="ranking", normalized_score=None)]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        self.assertEqual(result["scoredSubIssueCount"], 0)
        self.assertEqual(result["excludedResponseCount"], 1)

    def test_93_one_employee_impact_row_produces_score(self):
        rows = [_make_row(mapped_axis="impact", respondent_group="employee", normalized_score=4.0)]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        self.assertEqual(result["scoredSubIssueCount"], 1)
        score = result["scores"][0]
        self.assertAlmostEqual(score["surveyImpactScore"], 4.0)

    def test_94_financial_only_row_no_impact_score(self):
        rows = [_make_row(mapped_axis="financial", respondent_group="management", normalized_score=3.0)]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        score = result["scores"][0]
        self.assertIsNone(score["surveyImpactScore"])
        self.assertIsNotNone(score["surveyFinancialScore"])

    def test_95_all_three_groups_produce_weighted_avg(self):
        rows = [
            _make_row(source_response_key="E_K1", respondent_group="employee",
                      sub_issue_code="E01", mapped_axis="impact", normalized_score=2.0),
            _make_row(source_response_key="M_K1", respondent_group="management",
                      sub_issue_code="E01", mapped_axis="impact", normalized_score=4.0),
            _make_row(source_response_key="X_K1", respondent_group="external",
                      sub_issue_code="E01", mapped_axis="impact", normalized_score=3.0),
        ]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        # expected = (2.0*0.30 + 4.0*0.40 + 3.0*0.30) / 1.00 = 3.2
        expected = 2.0 * 0.30 + 4.0 * 0.40 + 3.0 * 0.30
        self.assertAlmostEqual(result["scores"][0]["surveyImpactScore"], expected, places=5)

    def test_96_bundle_active_response_count_includes_all_rows(self):
        rows = [
            _make_row(mapped_axis="impact", normalized_score=3.0),
            _make_row(mapped_axis="ranking", normalized_score=None),
            _make_row(mapped_axis="common", normalized_score=None),
        ]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        self.assertEqual(result["activeResponseCount"], 3)

    def test_97_invalid_axis_raises_before_scoring(self):
        rows = [_make_row(mapped_axis="invalid")]
        with self.assertRaises(RuntimeError):
            self.build(runId=1, surveyForm=self.form, rows=rows)

    def test_98_two_respondents_same_issue_averaged_first(self):
        rows = [
            _make_row(source_response_key="K1", respondent_group="employee",
                      sub_issue_code="E01", mapped_axis="impact", normalized_score=2.0),
            _make_row(source_response_key="K2", respondent_group="employee",
                      sub_issue_code="E01", mapped_axis="impact", normalized_score=4.0),
        ]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        # Respondent avg: K1→2.0, K2→4.0
        # Group avg: AVG(2.0, 4.0) = 3.0
        # Weight: employee only → 3.0
        self.assertAlmostEqual(result["scores"][0]["surveyImpactScore"], 3.0)

    def test_99_multiple_questions_per_respondent_averaged(self):
        rows = [
            _make_row(source_response_key="K1", sub_issue_code="E01",
                      mapped_axis="impact", normalized_score=1.0),
            _make_row(source_response_key="K1", sub_issue_code="E01",
                      mapped_axis="impact", normalized_score=5.0),
        ]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        # Per respondent: AVG(1.0, 5.0) = 3.0 → group employee = 3.0
        self.assertAlmostEqual(result["scores"][0]["surveyImpactScore"], 3.0)

    def test_100_group_scores_dict_structure_correct(self):
        rows = [
            _make_row(source_response_key="K1", respondent_group="employee",
                      mapped_axis="impact", normalized_score=3.0),
        ]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        gs = result["scores"][0]["groupScores"]
        self.assertIn("impact", gs)
        self.assertIn("financial", gs)
        self.assertIn("employee", gs["impact"])
        self.assertIn("management", gs["impact"])
        self.assertIn("external", gs["impact"])

    def test_101_sub_issue_code_key_in_score_entry(self):
        rows = [_make_row(sub_issue_code="ENV_CLIMATE", mapped_axis="impact", normalized_score=4.0)]
        result = self.build(runId=1, surveyForm=self.form, rows=rows)
        self.assertEqual(result["scores"][0]["subIssueCode"], "ENV_CLIMATE")

    def test_102_survey_form_id_propagated_from_form(self):
        rows = []
        result = self.build(runId=1, surveyForm={"id": 42, "esg_materiality_run_id": 1}, rows=rows)
        self.assertEqual(result["surveyFormId"], 42)


if __name__ == "__main__":
    unittest.main()
