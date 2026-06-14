"""
S4-A: Final Selection Persistence & Survey Result API QA — Test Suite
Tests:
  1. selected table 비어있으면 getMaterialityResults()가 RANK_FALLBACK 반환
  2. finalizeSelectedSubIssues() 실행 시 Top 5가 DB에 저장됨
  3. finalize 후 getMaterialityResults()가 TABLE/fallbackYn=false 반환
  4. finalize 후 getSelectionProcess() selectedIssues length = 5
  5. Top 5 후보 5개 미만이면 finalize는 ValueError
  6. listSurveyScores()가 mapped_axis별로 분리 집계
  7. getSurveyResult()가 axisSeparatedYn=true 반환
  8. listSurveyCounts()가 source_response_key distinct 기준 응답자 수 계산
"""
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_row(run_id=1):
    return {"id": run_id}


def _make_score_summary_rows(n=5):
    return [
        {
            "sub_issue_code": f"E_GHG_{i+1:02d}",
            "rank_no": i + 1,
            "final_score": 4.5 - i * 0.1,
            "final_impact_score": 4.3 - i * 0.1,
            "final_financial_score": 4.1 - i * 0.1,
            "benchmark_impact_score": None,
            "benchmark_financial_score": None,
            "media_external_impact_score": None,
            "media_external_financial_score": None,
            "survey_impact_score": None,
            "survey_financial_score": None,
        }
        for i in range(n)
    ]


def _make_conn():
    conn = MagicMock()
    conn.autocommit = True
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=cur)
    ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = ctx
    return conn, cur


# ---------------------------------------------------------------------------
# Test 1: empty selected table → RANK_FALLBACK
# ---------------------------------------------------------------------------

class TestGetMaterialityResultsFallback(unittest.TestCase):

    @patch("src.services.materialities.service.getLatestReportRun", return_value={})
    @patch("src.services.materialities.service.countMissingMetrics", return_value=0)
    @patch("src.services.materialities.service.countRequiredMetrics", return_value=3)
    @patch("src.services.materialities.service.listSelectedSubIssues", return_value=[])
    @patch("src.services.materialities.service.listResults")
    def test_01_empty_selected_table_returns_rank_fallback(
        self, mock_list, mock_sel, mock_req, mock_miss, mock_rep
    ):
        rows = _make_score_summary_rows(5)
        mock_list.return_value = rows

        from src.services.materialities.service import getMaterialityResults
        result = getMaterialityResults(runId=1)

        self.assertEqual(result.selectionSource, "RANK_FALLBACK")
        self.assertTrue(result.fallbackYn)


# ---------------------------------------------------------------------------
# Test 2: finalizeSelectedSubIssues → DB insert called
# ---------------------------------------------------------------------------

class TestFinalizeInsertsCalled(unittest.TestCase):

    @patch("src.services.materialities.service.replaceSelectedSubIssuesTx")
    @patch("src.services.materialities.service.listFinalTopSubIssues")
    @patch("src.services.materialities.service.findOne")
    @patch("src.services.materialities.service._initPostDmaScopeAfterFinalize")
    def test_02_finalize_calls_replace_tx(self, mock_scope, mock_run, mock_top, mock_replace):
        mock_run.return_value = {"id": 1}
        mock_top.return_value = _make_score_summary_rows(5)
        mock_replace.return_value = None
        mock_scope.return_value = None

        user = MagicMock()
        user.id = 42

        from src.services.materialities.service import finalizeSelectedSubIssues
        result = finalizeSelectedSubIssues(runId=1, userModel=user)

        mock_replace.assert_called_once()
        call_args = mock_replace.call_args
        self.assertEqual(call_args[0][0], 1)
        inserted = call_args[0][1]
        self.assertEqual(len(inserted), 5)
        self.assertEqual(inserted[0]["selected_rank_no"], 1)
        self.assertEqual(inserted[4]["selected_rank_no"], 5)
        self.assertEqual(call_args[1]["userId"], 42)

        # finalize는 선정 확정 직후 온보딩 지표 scope를 자동 초기화한다.
        mock_scope.assert_called_once_with(1, 42)


# ---------------------------------------------------------------------------
# Test 3: finalize → getMaterialityResults returns TABLE
# ---------------------------------------------------------------------------

class TestGetMaterialityResultsAfterFinalize(unittest.TestCase):

    @patch("src.services.materialities.service.getLatestReportRun", return_value={})
    @patch("src.services.materialities.service.countMissingMetrics", return_value=0)
    @patch("src.services.materialities.service.countRequiredMetrics", return_value=3)
    @patch("src.services.materialities.service.listSelectedSubIssues")
    @patch("src.services.materialities.service.listResults")
    def test_03_after_finalize_returns_table_source(
        self, mock_list, mock_sel, mock_req, mock_miss, mock_rep
    ):
        rows = _make_score_summary_rows(5)
        mock_list.return_value = rows
        mock_sel.return_value = [
            {"sub_issue_code": f"E_GHG_{i+1:02d}", "selected_rank_no": i+1,
             "selection_type": "rank_based", "selection_reason": "Top 5"}
            for i in range(5)
        ]

        from src.services.materialities.service import getMaterialityResults
        result = getMaterialityResults(runId=1)

        self.assertEqual(result.selectionSource, "TABLE")
        self.assertFalse(result.fallbackYn)
        self.assertEqual(result.selectedSubIssueCount, 5)


# ---------------------------------------------------------------------------
# Test 4: finalize → getSelectionProcess selectedIssues length = 5
# ---------------------------------------------------------------------------

class TestGetSelectionProcessAfterFinalize(unittest.TestCase):

    @patch("src.services.materialities.service.listSelectedSubIssues")
    @patch("src.services.materialities.service.listResults")
    def test_04_selection_process_selected_length_5(self, mock_list, mock_sel):
        rows = _make_score_summary_rows(8)
        mock_list.return_value = rows
        mock_sel.return_value = [
            {"sub_issue_code": f"E_GHG_{i+1:02d}", "selected_rank_no": i+1,
             "selection_type": "rank_based", "selection_reason": "Top 5"}
            for i in range(5)
        ]

        user = MagicMock()
        from src.services.materialities.service import getSelectionProcess
        result = getSelectionProcess(runId=1, userModel=user)

        self.assertEqual(result.selectionSource, "TABLE")
        self.assertFalse(result.fallbackYn)
        self.assertEqual(len(result.selectedIssues), 5)


# ---------------------------------------------------------------------------
# Test 5: fewer than 5 candidates → ValueError
# ---------------------------------------------------------------------------

class TestFinalizeFailsWithInsufficientCandidates(unittest.TestCase):

    @patch("src.services.materialities.service.listFinalTopSubIssues")
    @patch("src.services.materialities.service.findOne")
    def test_05_insufficient_candidates_raises_value_error(self, mock_run, mock_top):
        mock_run.return_value = {"id": 1}
        mock_top.return_value = _make_score_summary_rows(3)

        from src.services.materialities.service import finalizeSelectedSubIssues
        user = MagicMock()
        with self.assertRaises(ValueError) as ctx:
            finalizeSelectedSubIssues(runId=1, userModel=user)
        self.assertIn("3", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test 6: listSurveyScores groups by mapped_axis
# ---------------------------------------------------------------------------

class TestListSurveyScoresMappedAxis(unittest.TestCase):

    @patch("src.utils.dmarepository.findAll")
    def test_06_survey_scores_include_mapped_axis(self, mock_findall):
        mock_findall.return_value = [
            {"sub_issue_code": "E_GHG_01", "respondent_group": "employee",
             "mapped_axis": "impact", "avg_score": 3.5, "response_count": 10},
            {"sub_issue_code": "E_GHG_01", "respondent_group": "employee",
             "mapped_axis": "financial", "avg_score": 2.8, "response_count": 10},
        ]

        from src.utils.dmarepository import listSurveyScores
        rows = listSurveyScores(runId=1)

        self.assertEqual(len(rows), 2)
        axes = {r["mapped_axis"] for r in rows}
        self.assertIn("impact", axes)
        self.assertIn("financial", axes)

        sql_arg = mock_findall.call_args[0][0]
        self.assertIn("mapped_axis", sql_arg)
        self.assertIn("GROUP BY sub_issue_code, respondent_group, mapped_axis", sql_arg)


# ---------------------------------------------------------------------------
# Test 7: getSurveyResult → axisSeparatedYn = True
# ---------------------------------------------------------------------------

class TestGetSurveyResultAxisSeparated(unittest.TestCase):

    @patch("src.services.materialities.service.listSurveyScores", return_value=[])
    @patch("src.services.materialities.service.listTopStageIssues", return_value=[])
    @patch("src.services.materialities.service.listSurveyCounts", return_value=[])
    def test_07_survey_result_axis_separated_yn_true(
        self, mock_counts, mock_top, mock_scores
    ):
        from src.services.materialities.service import getSurveyResult
        result = getSurveyResult(runId=1)

        self.assertTrue(result.axisSeparatedYn)
        self.assertTrue(result.responseQuality.get("axisSeparatedYn"))
        self.assertNotIn("동일 반영", result.summaryText)


# ---------------------------------------------------------------------------
# Test 8: listSurveyCounts uses source_response_key distinct
# ---------------------------------------------------------------------------

class TestListSurveyCountsDistinct(unittest.TestCase):

    @patch("src.utils.dmarepository.findAll")
    def test_08_survey_counts_use_source_response_key_distinct(self, mock_findall):
        mock_findall.return_value = [
            {"respondent_group": "employee", "response_count": 5,
             "unique_respondent_count": 5},
        ]

        from src.utils.dmarepository import listSurveyCounts
        rows = listSurveyCounts(runId=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["response_count"], 5)

        sql_arg = mock_findall.call_args[0][0]
        self.assertIn("source_response_key", sql_arg)
        self.assertIn("DISTINCT source_response_key", sql_arg)
        self.assertNotIn("respondent_user_id", sql_arg)


if __name__ == "__main__":
    unittest.main()
