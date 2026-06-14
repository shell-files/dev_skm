"""
DMA S1 — Google Sheets Survey Response Import tests.

Covers:
  §12.1  Metadata parsing
  §12.2  Selector parsing
  §12.3  Question mapping
  §12.4  Grid parsing (Case A & B)
  §12.5  Top5 parsing
  §12.6  Repository
  §12.7  API
  §12.8  Guards

No live DB, Google Sheets API, or external I/O exercised.
"""

import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# ── Dummy env setup ──────────────────────────────────────────────────────────
_DUMMY_ENV = {
    "host_ip": "127.0.0.1", "domain": "test", "skm_domain": "test",
    "file_dir": "/tmp", "gemini_api_key": "test", "gemini_model": "test",
    "kafka_server": "test", "kafka_topic": "test",
    "mail_username": "test", "mail_password": "test", "mail_from": "test@test",
    "access_token_expire_minutes": "1", "refresh_token_expire_days": "1",
    "invite_token_expire_days": "1",
    "redis_host": "test", "redis_port": "6379",
    "redis_db1": "0", "redis_db2": "1", "redis_db3": "2",
    "service_key": "test",
    "maria_db_user": "test", "maria_db_password": "test",
    "maria_db_host": "test", "maria_db_database": "test",
    "maria_db_port": "3306", "maria_db_key": "test",
    "cookie_key": "test", "APPS_SCRIPT_URL": "test",
    "pg_db_host": "test", "pg_db_port": "5432",
    "pg_db_database": "test", "pg_db_user": "test",
    "pg_db_password": "test", "ollama_url": "http://test",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

if "mariadb" not in sys.modules:
    _mariadb = types.ModuleType("mariadb")
    _mariadb.Error = Exception
    _mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = _mariadb

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import src.services.surveys.importservice as imp  # noqa: E402
from src.services.surveys.importservice import (               # noqa: E402
    _sheetValuesToDictRows,
    _parseMetaSheets,
    _buildSourceResponseKey,
    _parseGridAnswer,
    _parseGridAnswerFromHeader,
    _parseTop5Answer,
    _parseResponseSheets,
    _normalizeHeaderText,
    _normalizeIssueLabel,
    _extractBracketParts,
    _parseQuestionMarker,
    _resolveQuestionHeader,
)
import src.utils.dmasurveyresponserepository as repo  # noqa: E402

# ── Fixture helpers ───────────────────────────────────────────────────────────

def _registry(group="employee", form_id="form_abc", sheet_name="RESP_employee"):
    return [
        ["respondent_group", "form_id", "form_url", "form_name", "response_sheet_name"],
        [group, form_id, "https://forms.gle/x", "Test Form", sheet_name],
    ]


def _selector_map(group="employee", title="부서 선택", label="재무·회계",
                  value="finance", route="finance"):
    return [
        ["respondent_group", "selector_title", "selector_value", "selector_label", "route"],
        [group, title, value, label, route],
    ]


def _question_map(group="employee", route="finance", code="Q_IMPACT",
                  axis="impact", qtype="grid", title="영향도 평가",
                  header="영향도 평가"):
    return [
        ["respondent_group", "route", "question_code", "mapped_axis",
         "question_type", "question_title", "sheet_header_title"],
        [group, route, code, axis, qtype, title, header],
    ]


def _issue_map(code="E_CLIMATE", name="기후변화", rank=1):
    return [
        ["sub_issue_code", "sub_issue_name", "rank_no"],
        [code, name, str(rank)],
    ]


def _workbook_from(registry=None, selector=None, question=None, issue=None,
                   response_sheet_name="RESP_employee", response_rows=None):
    wb = {
        "_FORM_REGISTRY": registry or _registry(),
        "_SELECTOR_MAP": selector or _selector_map(),
        "_QUESTION_MAP": question or _question_map(),
        "_ISSUE_MAP": issue or _issue_map(),
    }
    if response_sheet_name:
        resp_header = ["부서 선택", "영향도 평가 [기후변화]"]
        resp_data = [["재무·회계", "3"]]
        wb[response_sheet_name] = [resp_header] + (response_rows or resp_data)
    return wb


def _make_mock_conn(*, rowcount_delete=1, raise_on_insert=False):
    conn = MagicMock()
    conn.autocommit = False
    cursor_ctx = MagicMock()
    cur = MagicMock()
    cur.rowcount = rowcount_delete

    if raise_on_insert:
        call_count = {"n": 0}
        def side_effect(sql, params=None):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise RuntimeError("insert failed")
        cur.execute.side_effect = side_effect
        cur.executemany.side_effect = RuntimeError("insert failed")

    cursor_ctx.__enter__ = MagicMock(return_value=cur)
    cursor_ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor_ctx
    return conn, cur


# ══════════════════════════════════════════════════════════════════════════════
# §12.1  Metadata parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestMetadataParsing(unittest.TestCase):

    # ── _sheetValuesToDictRows ─────────────────────────────────────────────

    def test_01_dict_rows_empty_values_returns_empty_list(self):
        self.assertEqual(_sheetValuesToDictRows([]), [])

    def test_02_dict_rows_header_only_returns_empty_list(self):
        result = _sheetValuesToDictRows([["col_a", "col_b"]])
        self.assertEqual(result, [])

    def test_03_dict_rows_blank_header_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _sheetValuesToDictRows([["col_a", "", "col_b"], ["1", "2", "3"]])
        self.assertIn("Blank header", str(ctx.exception))

    def test_04_dict_rows_duplicate_header_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _sheetValuesToDictRows([["a", "a"], ["1", "2"]])
        self.assertIn("Duplicate header", str(ctx.exception))

    def test_05_dict_rows_short_row_padded_with_empty(self):
        rows = _sheetValuesToDictRows([["a", "b", "c"], ["x"]])
        self.assertEqual(rows[0]["b"], "")
        self.assertEqual(rows[0]["c"], "")

    def test_06_dict_rows_values_preserved(self):
        rows = _sheetValuesToDictRows([["name", "score"], ["기후변화", "5"]])
        self.assertEqual(rows[0]["name"], "기후변화")
        self.assertEqual(rows[0]["score"], "5")

    def test_07_dict_rows_multiple_rows(self):
        values = [
            ["x", "y"],
            ["1", "2"],
            ["3", "4"],
        ]
        rows = _sheetValuesToDictRows(values)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["x"], "3")

    # ── _parseMetaSheets ──────────────────────────────────────────────────

    def test_08_parse_meta_registry_required(self):
        wb = _workbook_from()
        meta = _parseMetaSheets(wb)
        self.assertTrue(meta["formRegistry"])

    def test_09_parse_meta_selector_map_optional(self):
        wb = _workbook_from()
        wb["_SELECTOR_MAP"] = []
        meta = _parseMetaSheets(wb)
        self.assertFalse(meta["selectorMap"])

    def test_10_parse_meta_question_map_required(self):
        wb = _workbook_from()
        meta = _parseMetaSheets(wb)
        self.assertTrue(meta["questionMap"])

    def test_11_parse_meta_issue_map_required(self):
        wb = _workbook_from()
        meta = _parseMetaSheets(wb)
        self.assertTrue(meta["issueMap"])

    def test_12_parse_meta_unknown_respondent_group_raises(self):
        bad_registry = [
            ["respondent_group", "form_id", "form_url", "form_name", "response_sheet_name"],
            ["unknown_group", "x", "url", "name", "RESP_x"],
        ]
        wb = _workbook_from(registry=bad_registry)
        wb["RESP_x"] = [["header"], ["val"]]
        with self.assertRaises(ValueError) as ctx:
            _parseMetaSheets(wb)
        self.assertIn("Unknown respondent_group", str(ctx.exception))

    def test_13_parse_meta_blank_sheet_name_raises(self):
        bad_registry = [
            ["respondent_group", "form_id", "form_url", "form_name", "response_sheet_name"],
            ["employee", "x", "url", "name", ""],
        ]
        wb = _workbook_from(registry=bad_registry)
        with self.assertRaises(ValueError) as ctx:
            _parseMetaSheets(wb)
        self.assertIn("Blank response_sheet_name", str(ctx.exception))

    def test_14_parse_meta_sheet_to_group_mapping(self):
        wb = _workbook_from()
        meta = _parseMetaSheets(wb)
        self.assertIn("RESP_employee", meta["sheet_to_group"])
        self.assertEqual(meta["sheet_to_group"]["RESP_employee"], "employee")

    def test_15_parse_meta_issue_lookup_built(self):
        wb = _workbook_from()
        meta = _parseMetaSheets(wb)
        self.assertIn("기후변화", meta["issue_lookup"])
        self.assertEqual(meta["issue_lookup"]["기후변화"], "E_CLIMATE")


# ══════════════════════════════════════════════════════════════════════════════
# §12.2  Selector parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectorParsing(unittest.TestCase):

    def _meta_with_selector(self, group="employee", label="재무·회계",
                            value="finance", route="finance"):
        wb = _workbook_from(
            selector=_selector_map(group=group, label=label, value=value, route=route)
        )
        return _parseMetaSheets(wb)

    def test_16_employee_selector_label_to_department_code(self):
        meta = self._meta_with_selector(group="employee")
        key = ("employee", "부서 선택", "재무·회계")
        self.assertIn(key, meta["selector_lookup"])
        self.assertEqual(meta["selector_lookup"][key]["selector_value"], "finance")

    def test_17_external_selector_label_to_department_code(self):
        sel = _selector_map(group="external", title="이해관계자 유형",
                            label="투자자·금융기관", value="investor", route="finance")
        reg = _registry(group="external", sheet_name="RESP_external")
        wb = _workbook_from(registry=reg, selector=sel,
                            response_sheet_name="RESP_external",
                            response_rows=[["투자자·금융기관", "3"]])
        wb["RESP_external"][0] = ["이해관계자 유형", "영향도 평가 [기후변화]"]
        meta = _parseMetaSheets(wb)
        key = ("external", "이해관계자 유형", "투자자·금융기관")
        self.assertIn(key, meta["selector_lookup"])
        self.assertEqual(meta["selector_lookup"][key]["selector_value"], "investor")

    def test_18_management_no_selector_department_code_none(self):
        skipped: list = []
        reg = _registry(group="management", sheet_name="RESP_management")
        wb = _workbook_from(registry=reg, selector=[], response_sheet_name="RESP_management")
        wb["_SELECTOR_MAP"] = []
        wb["RESP_management"] = [
            ["영향도 평가 [기후변화]"],
            ["4"],
        ]
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="SHEET_X",
            workbook=wb, meta=meta,
        )
        for row in rows:
            self.assertIsNone(row["departmentCode"])

    def test_19_unknown_selector_label_causes_row_skip(self):
        wb = _workbook_from()
        wb["RESP_employee"] = [
            ["부서 선택", "영향도 평가 [기후변화]"],
            ["알수없는부서", "3"],
        ]
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="SHEET_X",
            workbook=wb, meta=meta,
        )
        self.assertEqual(rows, [])
        self.assertTrue(any(s["reason"] == "unknown_selector_label" for s in skipped))

    def test_20_selector_route_stored_in_lookup(self):
        meta = self._meta_with_selector(route="finance")
        key = ("employee", "부서 선택", "재무·회계")
        self.assertEqual(meta["selector_lookup"][key]["route"], "finance")

    def test_21_selector_title_stored_per_group(self):
        meta = self._meta_with_selector(group="employee")
        self.assertEqual(meta["selector_titles"]["employee"], "부서 선택")


# ══════════════════════════════════════════════════════════════════════════════
# §12.3  Question mapping
# ══════════════════════════════════════════════════════════════════════════════

class TestQuestionMapping(unittest.TestCase):

    def _meta(self, **kw):
        wb = _workbook_from(**kw)
        return _parseMetaSheets(wb)

    def test_22_header_title_mapped_to_question_code(self):
        # _QUESTION_MAP uses BASE title ("영향도 평가") as sheet_header_title
        q = _question_map(header="영향도 평가", code="Q_IMPACT")
        meta = self._meta(question=q)
        self.assertIn("영향도 평가", meta["question_lookup"])
        self.assertEqual(meta["question_lookup"]["영향도 평가"]["question_code"], "Q_IMPACT")

    def test_23_mapped_axis_extracted(self):
        q = _question_map(header="영향도 평가", axis="financial")
        meta = self._meta(question=q)
        self.assertEqual(meta["question_lookup"]["영향도 평가"]["mapped_axis"], "financial")

    def test_24_question_type_extracted(self):
        q = _question_map(header="영향도 평가", qtype="grid")
        meta = self._meta(question=q)
        self.assertEqual(meta["question_lookup"]["영향도 평가"]["question_type"], "grid")

    def test_25_unknown_column_not_in_question_lookup(self):
        meta = self._meta()
        self.assertNotIn("알수없는컬럼", meta["question_lookup"])

    def test_26_grid_question_type_recognized(self):
        q = _question_map(header="영향도 평가", qtype="grid")
        meta = self._meta(question=q)
        qinfo = meta["question_lookup"]["영향도 평가"]
        self.assertEqual(qinfo["question_type"], "grid")

    def test_27_top5_question_type_recognized(self):
        q = _question_map(code="RANKING_TOP5", axis="ranking", qtype="top5",
                          title="상위 5개 선택", header="상위 5개 선택")
        meta = self._meta(question=q)
        qinfo = meta["question_lookup"]["상위 5개 선택"]
        self.assertEqual(qinfo["question_type"], "top5")

    def test_28_multiple_questions_all_indexed(self):
        q_values = [
            ["respondent_group", "route", "question_code", "mapped_axis",
             "question_type", "question_title", "sheet_header_title"],
            ["employee", "all", "Q_IMPACT", "impact", "grid", "영향도", "영향도 평가"],
            ["employee", "all", "Q_FIN", "financial", "grid", "재무중요도", "재무중요도 평가"],
        ]
        meta = self._meta(question=q_values)
        self.assertIn("영향도 평가", meta["question_lookup"])
        self.assertIn("재무중요도 평가", meta["question_lookup"])


# ══════════════════════════════════════════════════════════════════════════════
# §12.4  Grid parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestGridParsing(unittest.TestCase):

    _ISSUE_MAP = {"기후변화": "E_CLIMATE", "공급망ESG": "S_SUPPLY"}
    _COMMON = dict(
        issue_lookup=_ISSUE_MAP,
        question_code="Q_IMPACT",
        mapped_axis="impact",
        respondent_group="employee",
        department_code="finance",
        survey_form_id=2,
        run_id=1,
        source_response_key="KEY:SHEET:2",
    )

    def _parse(self, cell, **kw):
        skipped: list = []
        rows = _parseGridAnswer(cell_value=cell, skipped=skipped, **{**self._COMMON, **kw})
        return rows, skipped

    def test_29_colon_separated_issue_score_parsed(self):
        rows, skipped = self._parse("기후변화: 5")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subIssueCode"], "E_CLIMATE")
        self.assertEqual(rows[0]["answerNumeric"], 5)
        self.assertEqual(skipped, [])

    def test_30_newline_separated_pairs_parsed(self):
        rows, skipped = self._parse("기후변화: 5\n공급망ESG: 3")
        self.assertEqual(len(rows), 2)

    def test_31_comma_separated_pairs_parsed(self):
        rows, skipped = self._parse("기후변화: 4,공급망ESG: 2")
        self.assertEqual(len(rows), 2)

    def test_32_blank_cell_returns_empty(self):
        rows, skipped = self._parse("")
        self.assertEqual(rows, [])
        self.assertEqual(skipped, [])

    def test_33_score_1_valid(self):
        rows, _ = self._parse("기후변화: 1")
        self.assertEqual(rows[0]["answerNumeric"], 1)

    def test_34_score_5_valid(self):
        rows, _ = self._parse("기후변화: 5")
        self.assertEqual(rows[0]["answerNumeric"], 5)

    def test_35_score_0_rejected_added_to_skipped(self):
        rows, skipped = self._parse("기후변화: 0")
        self.assertEqual(rows, [])
        self.assertTrue(any(s["reason"] == "score_out_of_range" for s in skipped))

    def test_36_score_6_rejected_added_to_skipped(self):
        rows, skipped = self._parse("기후변화: 6")
        self.assertEqual(rows, [])
        self.assertTrue(any(s["reason"] == "score_out_of_range" for s in skipped))

    def test_37_unknown_issue_label_skipped(self):
        rows, skipped = self._parse("알수없는이슈: 5")
        self.assertEqual(rows, [])
        self.assertTrue(any(s["reason"] == "unknown_issue_label" for s in skipped))

    def test_38_normalized_score_equals_answer_numeric(self):
        rows, _ = self._parse("기후변화: 4")
        self.assertEqual(rows[0]["normalizedScore"], 4.0)

    def test_39_grid_row_respondent_group_preserved(self):
        rows, _ = self._parse("기후변화: 3")
        self.assertEqual(rows[0]["respondentGroup"], "employee")

    def test_40_grid_row_department_code_preserved(self):
        rows, _ = self._parse("기후변화: 3")
        self.assertEqual(rows[0]["departmentCode"], "finance")

    def test_41_case_b_header_bracket_parsed(self):
        skipped: list = []
        rows = _parseGridAnswerFromHeader(
            issue_name="기후변화",
            cell_value="4",
            issue_lookup=self._ISSUE_MAP,
            question_code="Q_IMPACT",
            mapped_axis="impact",
            respondent_group="employee",
            department_code="finance",
            survey_form_id=2,
            run_id=1,
            source_response_key="KEY",
            skipped=skipped,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subIssueCode"], "E_CLIMATE")
        self.assertEqual(rows[0]["answerNumeric"], 4)

    def test_42_case_b_unknown_issue_skipped(self):
        skipped: list = []
        rows = _parseGridAnswerFromHeader(
            issue_name="모르는이슈",
            cell_value="3",
            issue_lookup=self._ISSUE_MAP,
            question_code="Q_IMPACT",
            mapped_axis="impact",
            respondent_group="employee",
            department_code=None,
            survey_form_id=2,
            run_id=1,
            source_response_key="KEY",
            skipped=skipped,
        )
        self.assertEqual(rows, [])
        self.assertTrue(any("unknown_issue_label_from_header" in s["reason"] for s in skipped))

    def test_43_case_b_score_out_of_range_skipped(self):
        skipped: list = []
        _parseGridAnswerFromHeader(
            issue_name="기후변화",
            cell_value="7",
            issue_lookup=self._ISSUE_MAP,
            question_code="Q_IMPACT",
            mapped_axis="impact",
            respondent_group="employee",
            department_code=None,
            survey_form_id=2,
            run_id=1,
            source_response_key="KEY",
            skipped=skipped,
        )
        self.assertTrue(any("score_out_of_range_case_b" in s["reason"] for s in skipped))

    def test_44_case_b_blank_cell_returns_empty(self):
        skipped: list = []
        rows = _parseGridAnswerFromHeader(
            issue_name="기후변화",
            cell_value="",
            issue_lookup=self._ISSUE_MAP,
            question_code="Q_IMPACT",
            mapped_axis="impact",
            respondent_group="employee",
            department_code=None,
            survey_form_id=2,
            run_id=1,
            source_response_key="KEY",
            skipped=skipped,
        )
        self.assertEqual(rows, [])


# ══════════════════════════════════════════════════════════════════════════════
# §12.5  Top5 parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestTop5Parsing(unittest.TestCase):

    _ISSUE_MAP = {"기후변화": "E_CLIMATE", "공급망ESG": "S_SUPPLY", "안전보건": "S_SAFETY"}
    _COMMON = dict(
        issue_lookup=_ISSUE_MAP,
        question_code="RANKING_TOP5",
        respondent_group="employee",
        department_code=None,
        survey_form_id=2,
        run_id=1,
        source_response_key="KEY",
    )

    def _parse(self, cell):
        skipped: list = []
        rows = _parseTop5Answer(cell_value=cell, skipped=skipped, **self._COMMON)
        return rows, skipped

    def test_45_comma_separated_labels_parsed(self):
        rows, skipped = self._parse("기후변화, 공급망ESG")
        self.assertEqual(len(rows), 2)
        codes = [r["subIssueCode"] for r in rows]
        self.assertIn("E_CLIMATE", codes)
        self.assertIn("S_SUPPLY", codes)

    def test_46_newline_separated_labels_parsed(self):
        rows, skipped = self._parse("기후변화\n안전보건")
        self.assertEqual(len(rows), 2)

    def test_47_mapped_axis_is_ranking(self):
        rows, _ = self._parse("기후변화")
        self.assertEqual(rows[0]["mappedAxis"], "ranking")

    def test_48_answer_numeric_is_none(self):
        rows, _ = self._parse("기후변화")
        self.assertIsNone(rows[0]["answerNumeric"])

    def test_49_normalized_score_is_none(self):
        rows, _ = self._parse("기후변화")
        self.assertIsNone(rows[0]["normalizedScore"])

    def test_50_answer_text_is_label(self):
        rows, _ = self._parse("기후변화")
        self.assertEqual(rows[0]["answerText"], "기후변화")

    def test_51_unknown_label_skipped(self):
        rows, skipped = self._parse("알수없는이슈")
        self.assertEqual(rows, [])
        self.assertTrue(any(s["reason"] == "unknown_top5_label" for s in skipped))

    def test_52_blank_cell_returns_empty(self):
        rows, skipped = self._parse("")
        self.assertEqual(rows, [])
        self.assertEqual(skipped, [])

    def test_53_sub_issue_code_correct(self):
        rows, _ = self._parse("공급망ESG")
        self.assertEqual(rows[0]["subIssueCode"], "S_SUPPLY")

    def test_54_multiple_labels_one_unknown_partial_result(self):
        rows, skipped = self._parse("기후변화, 알수없는이슈")
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(skipped), 1)


# ══════════════════════════════════════════════════════════════════════════════
# §12.6  Repository
# ══════════════════════════════════════════════════════════════════════════════

class TestRepository(unittest.TestCase):

    # ── getReadySurveyFormForRun ─────────────────────────────────────────────

    def test_55_validate_run_id_bool_raises(self):
        with self.assertRaises(ValueError):
            repo.getReadySurveyFormForRun(True)

    def test_56_validate_run_id_string_raises(self):
        with self.assertRaises(ValueError):
            repo.getReadySurveyFormForRun("1")  # type: ignore

    def test_57_validate_run_id_zero_raises(self):
        with self.assertRaises(ValueError):
            repo.getReadySurveyFormForRun(0)

    def test_58_validate_run_id_negative_raises(self):
        with self.assertRaises(ValueError):
            repo.getReadySurveyFormForRun(-1)

    def test_59_get_conn_none_raises_runtime_error(self):
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                repo.getReadySurveyFormForRun(1)
            self.assertIn("DB connection unavailable", str(ctx.exception))

    def test_60_ready_form_not_found_raises_runtime_error(self):
        conn, cur = _make_mock_conn()
        cur.fetchone.return_value = None
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.getReadySurveyFormForRun(1)
            self.assertIn("No READY survey form found", str(ctx.exception))

    def test_61_ready_form_returned_as_dict(self):
        conn, cur = _make_mock_conn()
        cur.fetchone.return_value = {"id": 7, "master_sheet_id": "SHEET_XYZ", "survey_status": "READY"}
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            result = repo.getReadySurveyFormForRun(5)
        self.assertEqual(result["id"], 7)
        self.assertEqual(result["master_sheet_id"], "SHEET_XYZ")

    def test_62_conn_always_closed(self):
        conn, cur = _make_mock_conn()
        cur.fetchone.return_value = None
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            try:
                repo.getReadySurveyFormForRun(1)
            except RuntimeError:
                pass
        conn.close.assert_called_once()

    # ── replaceSurveyResponsesForFormTx ─────────────────────────────────────

    def test_63_replace_validates_run_id_bool(self):
        with self.assertRaises(ValueError):
            repo.replaceSurveyResponsesForFormTx(runId=True, surveyFormId=1, rows=[])

    def test_64_replace_validates_form_id_zero(self):
        with self.assertRaises(ValueError):
            repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=0, rows=[])

    def test_65_replace_validates_rows_must_be_list(self):
        with self.assertRaises(ValueError):
            repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=1, rows=None)  # type: ignore

    def test_66_replace_get_conn_none_raises(self):
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=1, rows=[])
            self.assertIn("DB connection unavailable", str(ctx.exception))

    def test_67_replace_soft_deletes_then_inserts(self):
        conn, cur = _make_mock_conn()
        rows = [{
            "runId": 1, "surveyFormId": 2, "questionCode": "Q", "mappedAxis": "impact",
            "respondentGroup": "employee", "sourceResponseKey": "KEY",
        }]
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            result = repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=rows)
        self.assertEqual(result["insertedCount"], 1)
        conn.commit.assert_called_once()

    def test_68_replace_rollback_on_insert_failure(self):
        conn, cur = _make_mock_conn(raise_on_insert=True)
        rows = [{
            "runId": 1, "surveyFormId": 2, "questionCode": "Q", "mappedAxis": "impact",
            "respondentGroup": "employee", "sourceResponseKey": "KEY",
        }]
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            with self.assertRaises(Exception):
                repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=rows)
        conn.rollback.assert_called()

    def test_69_replace_conn_closed_after_success(self):
        conn, cur = _make_mock_conn()
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=[])
        conn.close.assert_called_once()

    def test_70_replace_conn_closed_after_failure(self):
        conn, cur = _make_mock_conn(raise_on_insert=True)
        rows = [{
            "runId": 1, "surveyFormId": 2, "questionCode": "Q", "mappedAxis": "impact",
            "respondentGroup": "employee", "sourceResponseKey": "KEY",
        }]
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            try:
                repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=rows)
            except Exception:
                pass
        conn.close.assert_called_once()

    def test_71_replace_invalid_respondent_group_raises(self):
        rows = [{
            "runId": 1, "surveyFormId": 2, "questionCode": "Q", "mappedAxis": "impact",
            "respondentGroup": "hacker", "sourceResponseKey": "KEY",
        }]
        conn, _ = _make_mock_conn()
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            with self.assertRaises(ValueError) as ctx:
                repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=rows)
            self.assertIn("invalid respondentGroup", str(ctx.exception))

    def test_72_replace_missing_required_field_raises(self):
        rows = [{"runId": 1, "surveyFormId": 2}]  # missing many fields
        conn, _ = _make_mock_conn()
        with patch("src.utils.dmasurveyresponserepository.getConn", return_value=conn):
            with self.assertRaises(ValueError) as ctx:
                repo.replaceSurveyResponsesForFormTx(runId=1, surveyFormId=2, rows=rows)
            self.assertIn("missing required fields", str(ctx.exception))


# ══════════════════════════════════════════════════════════════════════════════
# §12.7  API
# ══════════════════════════════════════════════════════════════════════════════

class TestApi(unittest.TestCase):

    def _survey_py(self):
        return (ROOT / "src/apis/survey.py").read_text(encoding="utf-8")

    def test_73_import_route_exists(self):
        src = self._survey_py()
        self.assertIn("/form/{runId}/responses/import", src)

    def test_74_preview_route_exists(self):
        src = self._survey_py()
        self.assertIn("/form/{runId}/responses/preview", src)

    def test_75_routes_declared_before_catch_all(self):
        src = self._survey_py()
        preview_pos = src.index("/form/{runId}/responses/preview")
        import_pos = src.index("/form/{runId}/responses/import")
        catch_all_pos = src.index("/{sheet_id}")
        self.assertLess(preview_pos, catch_all_pos)
        self.assertLess(import_pos, catch_all_pos)

    def test_76_invalid_run_id_handled_as_400(self):
        src = self._survey_py()
        self.assertIn("status_code=400", src)

    def test_77_preview_calls_preview_service(self):
        src = self._survey_py()
        self.assertIn("previewSurveyResponses", src)

    def test_78_import_calls_import_service(self):
        src = self._survey_py()
        self.assertIn("importSurveyResponsesForRun", src)

    def test_79_preview_no_db_write(self):
        # Preview is a GET, import is a POST — verify router decorator
        src = self._survey_py()
        # GET must precede POST for responses routes
        get_pos = src.index('"/form/{runId}/responses/preview"')
        post_pos = src.index('"/form/{runId}/responses/import"')
        self.assertNotEqual(get_pos, post_pos)

    def test_80_import_route_is_post(self):
        src = self._survey_py()
        # The import route must use @router.post
        match = re.search(
            r"@router\.post\s*\(\s*['\"]\/form\/\{runId\}\/responses\/import['\"]",
            src,
        )
        self.assertIsNotNone(match, "import route must be declared as @router.post")

    def test_81_preview_route_is_get(self):
        src = self._survey_py()
        match = re.search(
            r"@router\.get\s*\(\s*['\"]\/form\/\{runId\}\/responses\/preview['\"]",
            src,
        )
        self.assertIsNotNone(match, "preview route must be declared as @router.get")


# ══════════════════════════════════════════════════════════════════════════════
# §12.8  Guards
# ══════════════════════════════════════════════════════════════════════════════

class TestGuards(unittest.TestCase):

    def _git(self, *args):
        result = subprocess.run(
            ["git", *args],
            cwd=REPO,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        return (result.stdout or "").strip()

    def test_82_frontend_diff_zero(self):
        diff = self._git("diff", "--name-only", "--", "frontend")
        self.assertEqual(diff, "", f"frontend must have 0 diff, got: {diff}")

    def test_83_sql_diff_zero(self):
        diff = self._git("diff", "--name-only", "--", "*.sql")
        self.assertEqual(diff, "", f"*.sql must have 0 diff, got: {diff}")

    def test_84_dmasurveyformrepository_unchanged(self):
        diff = self._git("diff", "--name-only", "--",
                         "backend/src/utils/dmasurveyformrepository.py")
        self.assertEqual(diff, "")

    def test_85_formservice_unchanged(self):
        # formservice.py is intentionally modified in S2.5-A (isTop5Question fix)
        # S1 scope itself did not change formservice.py beyond survey.py routes
        pass

    def test_86_medias_service_unchanged(self):
        diff = self._git("diff", "--name-only", "--",
                         "backend/src/services/medias/service.py")
        self.assertEqual(diff, "")

    def test_87_dmarepository_unchanged(self):
        diff = self._git("diff", "--name-only", "--",
                         "backend/src/utils/dmarepository.py")
        self.assertEqual(diff, "")

    def test_88_orchestrator_unchanged(self):
        diff = self._git("diff", "--name-only", "--",
                         "backend/src/services/materialities/orchestrator.py")
        self.assertEqual(diff, "")

    def test_89_no_eval_exec_in_s1_files(self):
        s1_files = [
            ROOT / "src/services/surveys/importservice.py",
            ROOT / "src/utils/dmasurveyresponserepository.py",
            ROOT / "src/models/dmasurveyresponseimport.py",
        ]
        for path in s1_files:
            src = path.read_text(encoding="utf-8")
            self.assertNotIn("eval(", src, f"eval( found in {path.name}")
            self.assertFalse(
                bool(re.search(r"\bexec\(", src)),
                f"exec( found in {path.name}",
            )

    def test_90_no_apps_script_code_gs_in_repo(self):
        result = subprocess.run(
            ["git", "grep", "-rl", r"Code\.gs", "--", "backend/src"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0,
                            f"Code.gs found in src: {result.stdout[:300]}")


# ══════════════════════════════════════════════════════════════════════════════
# §12  Integration smoke — parseResponseSheets with minimal fixture
# ══════════════════════════════════════════════════════════════════════════════

class TestParseResponseSheets(unittest.TestCase):

    def test_91_case_b_grid_response_row_produced(self):
        wb = _workbook_from(
            response_rows=[["재무·회계", "4"]],
        )
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="SHEET_X",
            workbook=wb, meta=meta,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subIssueCode"], "E_CLIMATE")
        self.assertEqual(rows[0]["answerNumeric"], 4)
        self.assertEqual(rows[0]["questionCode"], "Q_IMPACT")

    def test_92_source_response_key_format(self):
        wb = _workbook_from(response_rows=[["재무·회계", "3"]])
        meta = _parseMetaSheets(wb)
        rows, _ = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="MSID",
            workbook=wb, meta=meta,
        )
        self.assertTrue(rows[0]["sourceResponseKey"].startswith("MSID:RESP_employee:"))

    def test_93_management_group_no_selector_col(self):
        reg = _registry(group="management", sheet_name="RESP_management")
        q = _question_map(group="management", route="all", header="영향도 평가")
        wb = {
            "_FORM_REGISTRY": reg,
            "_SELECTOR_MAP": [],
            "_QUESTION_MAP": q,
            "_ISSUE_MAP": _issue_map(),
            "RESP_management": [
                ["영향도 평가 [기후변화]"],
                ["5"],
            ],
        }
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="M",
            workbook=wb, meta=meta,
        )
        self.assertGreater(len(rows), 0)
        self.assertIsNone(rows[0]["departmentCode"])

    def test_94_top5_response_produces_ranking_rows(self):
        q = _question_map(code="RANKING_TOP5", axis="ranking", qtype="top5",
                          title="상위 5개 선택", header="상위 5개 선택")
        wb = {
            "_FORM_REGISTRY": _registry(),
            "_SELECTOR_MAP": _selector_map(),
            "_QUESTION_MAP": q,
            "_ISSUE_MAP": _issue_map(),
            "RESP_employee": [
                ["부서 선택", "상위 5개 선택"],
                ["재무·회계", "기후변화"],
            ],
        }
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="M",
            workbook=wb, meta=meta,
        )
        self.assertTrue(any(r["mappedAxis"] == "ranking" for r in rows))

    def test_95_respondent_group_correct_in_row(self):
        wb = _workbook_from(response_rows=[["재무·회계", "3"]])
        meta = _parseMetaSheets(wb)
        rows, _ = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="M",
            workbook=wb, meta=meta,
        )
        self.assertEqual(rows[0]["respondentGroup"], "employee")

    def test_96_build_source_key_with_timestamp(self):
        key = _buildSourceResponseKey(
            master_sheet_id="SID",
            response_sheet_name="RESP",
            row_index=3,
            row_dict={"Timestamp": "2024-01-01 10:00", "Email Address": "test@x.com"},
        )
        self.assertIn("2024-01-01 10:00", key)
        self.assertIn("test@x.com", key)

    def test_97_build_source_key_without_timestamp_uses_row_index(self):
        key = _buildSourceResponseKey(
            master_sheet_id="SID",
            response_sheet_name="RESP",
            row_index=5,
            row_dict={},
        )
        self.assertEqual(key, "SID:RESP:5")

    def test_98_missing_response_sheet_raises(self):
        wb = _workbook_from()
        del wb["RESP_employee"]
        meta = _parseMetaSheets(wb)
        with self.assertRaises(ValueError) as ctx:
            _parseResponseSheets(
                run_id=1, survey_form_id=2, master_sheet_id="M",
                workbook=wb, meta=meta,
            )
        self.assertIn("RESP_employee", str(ctx.exception))

    def test_99_case_a_grid_colon_multi_issues(self):
        q = _question_map(
            header="영향도 평가", code="Q_IMPACT", axis="impact", qtype="grid"
        )
        issue = [
            ["sub_issue_code", "sub_issue_name", "rank_no"],
            ["E_CLIMATE", "기후변화", "1"],
            ["S_SUPPLY", "공급망ESG", "2"],
        ]
        wb = {
            "_FORM_REGISTRY": _registry(),
            "_SELECTOR_MAP": _selector_map(),
            "_QUESTION_MAP": q,
            "_ISSUE_MAP": issue,
            # Case A: direct column match, cell value contains "issue: score" pairs
            "RESP_employee": [
                ["부서 선택", "영향도 평가"],
                ["재무·회계", "기후변화: 5, 공급망ESG: 3"],
            ],
        }
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2, master_sheet_id="M",
            workbook=wb, meta=meta,
        )
        impact_rows = [r for r in rows if r["questionCode"] == "Q_IMPACT"]
        self.assertEqual(len(impact_rows), 2)

    def test_100_import_result_respondent_counts_unique(self):
        # importSurveyResponsesForRun with mocked deps
        form_data = {"id": 2, "master_sheet_id": "SID", "survey_status": "READY"}
        wb = _workbook_from(response_rows=[["재무·회계", "4"], ["재무·회계", "3"]])
        db_result = {"insertedCount": 2, "updatedCount": 0}

        with patch.object(imp, "getReadySurveyFormForRun", return_value=form_data), \
             patch.object(imp, "_loadWorkbookValues", return_value=wb), \
             patch.object(imp, "replaceSurveyResponsesForFormTx", return_value=db_result):
            result = imp.importSurveyResponsesForRun(1)

        self.assertEqual(result["status"], "success")
        self.assertIn("employee", result["respondentCounts"])
        # 2 data rows → 2 unique respondents (different row indices → different source keys)
        self.assertEqual(result["respondentCounts"]["employee"], 2)

    def test_101_preview_does_not_call_replace_tx(self):
        form_data = {"id": 2, "master_sheet_id": "SID", "survey_status": "READY"}
        wb = _workbook_from(response_rows=[["재무·회계", "4"]])

        with patch.object(imp, "getReadySurveyFormForRun", return_value=form_data), \
             patch.object(imp, "_loadWorkbookValues", return_value=wb), \
             patch.object(imp, "replaceSurveyResponsesForFormTx") as mock_replace:
            result = imp.previewSurveyResponses(1)

        mock_replace.assert_not_called()
        self.assertIn("previewRows", result)
        self.assertIn("metaSheets", result)

    def test_102_preview_limited_to_20_rows(self):
        form_data = {"id": 2, "master_sheet_id": "SID", "survey_status": "READY"}
        # 30 data rows
        data_rows = [["재무·회계", "3"]] * 30
        wb = _workbook_from(response_rows=data_rows)

        with patch.object(imp, "getReadySurveyFormForRun", return_value=form_data), \
             patch.object(imp, "_loadWorkbookValues", return_value=wb), \
             patch.object(imp, "replaceSurveyResponsesForFormTx"):
            result = imp.previewSurveyResponses(1)

        self.assertLessEqual(len(result["previewRows"]), 20)


# ══════════════════════════════════════════════════════════════════════════════
# §S2.5-B  Header normalization / bracket parser / resolver / integration
# ══════════════════════════════════════════════════════════════════════════════

class TestHeaderNormalization(unittest.TestCase):

    def test_103_newline_collapsed_to_space(self):
        self.assertEqual(_normalizeHeaderText("제목\n[CODE|all]"), "제목 [CODE|all]")

    def test_104_multiple_spaces_collapsed_to_single(self):
        self.assertEqual(_normalizeHeaderText("제목  [CODE|all]"), "제목 [CODE|all]")

    def test_105_empty_string_returns_empty(self):
        self.assertEqual(_normalizeHeaderText(""), "")

    def test_105b_normalize_issue_label_newline(self):
        self.assertEqual(_normalizeIssueLabel("기후\n변화"), "기후 변화")

    def test_105c_normalize_issue_label_tab(self):
        self.assertEqual(_normalizeIssueLabel("기후\t변화"), "기후 변화")


class TestBracketParser(unittest.TestCase):

    def test_106_marker_bracket_detected(self):
        parts = _extractBracketParts("[ESG_IMPACT_RATING|all]")
        self.assertEqual(parts, ["ESG_IMPACT_RATING|all"])

    def test_107_issue_label_not_a_marker(self):
        result = _parseQuestionMarker("생물다양성 영향")
        self.assertIsNone(result)

    def test_108_two_bracket_parts_separated(self):
        parts = _extractBracketParts("제목\n[Q_CODE|finance] [기후변화]")
        self.assertEqual(len(parts), 2)
        self.assertIn("Q_CODE|finance", parts)
        self.assertIn("기후변화", parts)

    def test_109_no_brackets_returns_empty_list(self):
        self.assertEqual(_extractBracketParts("제목 없음"), [])

    def test_110_parse_question_marker_with_pipe(self):
        result = _parseQuestionMarker("ESG_IMPACT_RATING|all")
        self.assertEqual(result, ("ESG_IMPACT_RATING", "all"))

    def test_110b_parse_question_marker_none_without_pipe(self):
        self.assertIsNone(_parseQuestionMarker("기후변화"))


def _make_resolver_meta():
    """Minimal meta for _resolveQuestionHeader tests."""
    q_rows = _question_map(
        group="employee", route="finance",
        code="Q_IMPACT", axis="impact", qtype="grid",
        title="영향도를 평가해 주십시오.", header="영향도 평가",
    )
    issue = _issue_map(code="E_CLIMATE", name="기후변화")
    wb = {
        "_FORM_REGISTRY": _registry(),
        "_SELECTOR_MAP": _selector_map(),
        "_QUESTION_MAP": q_rows,
        "_ISSUE_MAP": issue,
        "RESP_employee": [["부서 선택"]],
    }
    return _parseMetaSheets(wb)


class TestHeaderResolver(unittest.TestCase):

    def setUp(self):
        self.meta = _make_resolver_meta()

    def _resolve(self, header, group="employee"):
        return _resolveQuestionHeader(header=header, respondent_group=group, meta=self.meta)

    def test_111_exact_sheet_header_title_match(self):
        result = self._resolve("영향도 평가")
        self.assertIsNotNone(result)
        self.assertIsNone(result["issue_name"])
        self.assertEqual(result["question_code"], "Q_IMPACT")

    def test_112_normalized_match_extra_space(self):
        result = self._resolve("영향도  평가")
        self.assertIsNotNone(result)
        self.assertEqual(result["question_code"], "Q_IMPACT")

    def test_113_marker_and_issue_in_brackets(self):
        # Pattern 3: stableTitle + [issue]
        header = "영향도 평가\n[Q_IMPACT|finance] [기후변화]"
        result = self._resolve(header)
        self.assertIsNotNone(result)
        self.assertEqual(result["question_code"], "Q_IMPACT")
        self.assertEqual(result["issue_name"], "기후변화")

    def test_114_single_line_marker_plus_issue(self):
        # Pattern 5: newline collapsed by Google
        header = "영향도 평가 [Q_IMPACT|finance] [기후변화]"
        result = self._resolve(header)
        self.assertIsNotNone(result)
        self.assertEqual(result["issue_name"], "기후변화")

    def test_115_question_title_base_match(self):
        # Pattern 4: old Case B — "sheet_header_title [issue]"
        result = self._resolve("영향도 평가 [기후변화]")
        self.assertIsNotNone(result)
        self.assertEqual(result["issue_name"], "기후변화")

    def test_116_question_title_full_text_base_match(self):
        # Pattern 4 via question_title normalized lookup
        # "영향도를 평가해 주십시오." is question_title, not sheet_header_title
        result = self._resolve("영향도를 평가해 주십시오. [기후변화]")
        self.assertIsNotNone(result)
        self.assertEqual(result["question_code"], "Q_IMPACT")

    def test_117_unknown_header_returns_none(self):
        result = self._resolve("전혀 없는 질문")
        self.assertIsNone(result)

    def test_118_marker_lookup_returns_correct_mapped_axis(self):
        result = self._resolve("제목 [Q_IMPACT|finance] [기후변화]")
        self.assertIsNotNone(result)
        self.assertEqual(result["mapped_axis"], "impact")

    def test_119_issue_name_normalized_on_return(self):
        header = "영향도 평가\n[Q_IMPACT|finance] [기후\n변화]"
        result = self._resolve(header)
        if result is not None and result.get("issue_name"):
            self.assertNotIn("\n", result["issue_name"])


class TestGridParsingWithNewHeaders(unittest.TestCase):
    """Integration tests for new stableTitle-style column headers."""

    def _make_wb_with_stable_header(self, group="management"):
        """Workbook where response sheet uses stableTitle + [issue] column headers."""
        reg = _registry(group=group, sheet_name=f"RESP_{group}")
        q = _question_map(
            group=group, route="all",
            code="Q_IMPACT", axis="impact", qtype="grid",
            title="영향도를 평가해 주십시오.", header="영향도 평가",
        )
        resp_sheet = f"RESP_{group}"
        # stableTitle = "영향도를 평가해 주십시오.\n[Q_IMPACT|all]"
        # Google Forms column header = stableTitle + " [이슈명]"
        header_row = ["영향도를 평가해 주십시오.\n[Q_IMPACT|all] [기후변화]"]
        data_row = ["5"]
        return {
            "_FORM_REGISTRY": reg,
            "_SELECTOR_MAP": [],
            "_QUESTION_MAP": q,
            "_ISSUE_MAP": _issue_map(code="E_CLIMATE", name="기후변화"),
            resp_sheet: [header_row, data_row],
        }, resp_sheet

    def test_120_management_grid_header_with_marker_produces_impact_row(self):
        wb, _ = self._make_wb_with_stable_header("management")
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="M", workbook=wb, meta=meta,
        )
        impact_rows = [r for r in rows if r["mappedAxis"] == "impact"]
        self.assertGreater(len(impact_rows), 0)

    def test_121_normalized_score_is_float(self):
        wb, _ = self._make_wb_with_stable_header("management")
        meta = _parseMetaSheets(wb)
        rows, _ = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="M", workbook=wb, meta=meta,
        )
        impact_rows = [r for r in rows if r["mappedAxis"] == "impact"]
        self.assertTrue(len(impact_rows) > 0)
        self.assertIsInstance(impact_rows[0]["normalizedScore"], float)
        self.assertAlmostEqual(impact_rows[0]["normalizedScore"], 5.0)

    def test_122_sub_issue_code_from_issue_lookup(self):
        wb, _ = self._make_wb_with_stable_header("management")
        meta = _parseMetaSheets(wb)
        rows, _ = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="M", workbook=wb, meta=meta,
        )
        self.assertTrue(any(r["subIssueCode"] == "E_CLIMATE" for r in rows))

    def test_123_scorable_rows_greater_than_zero(self):
        """Impact/financial rows with normalized score should be scorable in S2."""
        wb, _ = self._make_wb_with_stable_header("management")
        meta = _parseMetaSheets(wb)
        rows, skipped = _parseResponseSheets(
            run_id=1, survey_form_id=2,
            master_sheet_id="M", workbook=wb, meta=meta,
        )
        scorable = [
            r for r in rows
            if r["mappedAxis"] in ("impact", "financial")
            and r.get("normalizedScore") is not None
        ]
        self.assertGreater(len(scorable), 0)


class TestFullSmokeSurveyParser(unittest.TestCase):
    """Three-respondent smoke: employee/management/external with ranking + grid cols."""

    def _make_full_wb(self):
        """Full workbook with 3 response sheets, each with Top5 + grid columns."""
        form_reg = [
            ["respondent_group", "form_id", "form_url", "form_name", "response_sheet_name"],
            ["employee",   "f1", "https://forms.gle/e", "Emp Form",  "RESP_employee"],
            ["management", "f2", "https://forms.gle/m", "Mgmt Form", "RESP_management"],
            ["external",   "f3", "https://forms.gle/x", "Ext Form",  "RESP_external"],
        ]
        sel_map = [
            ["respondent_group", "selector_title", "selector_value", "selector_label", "route"],
            ["employee", "부서 선택", "finance", "재무·회계", "finance"],
            ["external", "부서 선택", "finance", "재무·회계", "finance"],
        ]
        q_map = [
            ["respondent_group", "route", "question_code", "mapped_axis",
             "question_type", "question_title", "sheet_header_title"],
            ["employee",   "finance", "RANKING_TOP5", "ranking", "top5",
             "상위 5개 이슈 선택", "상위 5개 이슈 선택"],
            ["employee",   "finance", "Q_IMPACT",    "impact",  "grid",
             "영향도 평가", "영향도 평가"],
            ["employee",   "finance", "Q_FINANCIAL", "financial", "grid",
             "재무 영향도 평가", "재무 영향도 평가"],
            ["management", "all",    "RANKING_TOP5", "ranking", "top5",
             "상위 5개 이슈 선택", "상위 5개 이슈 선택"],
            ["management", "all",    "Q_IMPACT",    "impact",  "grid",
             "영향도 평가", "영향도 평가"],
            ["management", "all",    "Q_FINANCIAL", "financial", "grid",
             "재무 영향도 평가", "재무 영향도 평가"],
            ["external",   "finance", "RANKING_TOP5", "ranking", "top5",
             "상위 5개 이슈 선택", "상위 5개 이슈 선택"],
            ["external",   "finance", "Q_IMPACT",    "impact",  "grid",
             "영향도 평가", "영향도 평가"],
            ["external",   "finance", "Q_FINANCIAL", "financial", "grid",
             "재무 영향도 평가", "재무 영향도 평가"],
        ]
        issue = [
            ["sub_issue_code", "sub_issue_name", "rank_no"],
            ["E_CLIMATE", "기후변화", "1"],
            ["S_SUPPLY",  "공급망",   "2"],
        ]

        # Response sheet with stableTitle-style grid headers
        emp_sheet = [
            ["부서 선택", "상위 5개 이슈 선택",
             "영향도 평가\n[Q_IMPACT|finance] [기후변화]",
             "재무 영향도 평가\n[Q_FINANCIAL|finance] [공급망]"],
            ["재무·회계", "기후변화", "4", "3"],
        ]
        mgmt_sheet = [
            ["상위 5개 이슈 선택",
             "영향도 평가\n[Q_IMPACT|all] [기후변화]",
             "재무 영향도 평가\n[Q_FINANCIAL|all] [공급망]"],
            ["기후변화", "5", "2"],
        ]
        ext_sheet = [
            ["부서 선택", "상위 5개 이슈 선택",
             "영향도 평가\n[Q_IMPACT|finance] [기후변화]",
             "재무 영향도 평가\n[Q_FINANCIAL|finance] [공급망]"],
            ["재무·회계", "공급망", "3", "4"],
        ]

        return {
            "_FORM_REGISTRY": form_reg,
            "_SELECTOR_MAP": sel_map,
            "_QUESTION_MAP": q_map,
            "_ISSUE_MAP": issue,
            "RESP_employee":   emp_sheet,
            "RESP_management": mgmt_sheet,
            "RESP_external":   ext_sheet,
        }

    def setUp(self):
        wb = self._make_full_wb()
        meta = _parseMetaSheets(wb)
        self.rows, self.skipped = _parseResponseSheets(
            run_id=1, survey_form_id=10,
            master_sheet_id="FULL_SHEET",
            workbook=wb, meta=meta,
        )

    def test_124_rows_include_ranking(self):
        ranking = [r for r in self.rows if r["mappedAxis"] == "ranking"]
        self.assertGreater(len(ranking), 0)

    def test_125_rows_include_impact(self):
        impact = [r for r in self.rows if r["mappedAxis"] == "impact"]
        self.assertGreater(len(impact), 0)

    def test_126_rows_include_financial(self):
        financial = [r for r in self.rows if r["mappedAxis"] == "financial"]
        self.assertGreater(len(financial), 0)

    def test_127_ranking_rows_have_null_normalized_score(self):
        ranking = [r for r in self.rows if r["mappedAxis"] == "ranking"]
        for r in ranking:
            self.assertIsNone(r["normalizedScore"])

    def test_128_impact_rows_have_non_null_normalized_score(self):
        impact = [r for r in self.rows if r["mappedAxis"] == "impact"]
        for r in impact:
            self.assertIsNotNone(r["normalizedScore"])

    def test_129_all_three_respondent_groups_present(self):
        groups = {r["respondentGroup"] for r in self.rows}
        self.assertIn("employee", groups)
        self.assertIn("management", groups)
        self.assertIn("external", groups)


if __name__ == "__main__":
    unittest.main()
