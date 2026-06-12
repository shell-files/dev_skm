"""
DMA v1.3 Phase C2.0 — media_external.news Fact Resolver tests.

Pure unit tests. No live DB, API smoke, Redis, Kafka, Docker, or external API path
is exercised.

Coverage:
- step0NormalizeMediaFacts: Fail-Fast, sourceType, provider metadata,
  provenance, event fact passthrough, no-guess, forbidden contamination
- buildEvidenceSpan: teCrawlingId passthrough
- manifest capability: mediaEventCanonicalAdapter == CONFIG_PENDING
"""

import json
import os
import sys
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

from src.models.dmaengine import EvidenceSpanV13, ExtractedFactsV13  # noqa: E402
from src.services.medias.adapter import buildEvidenceSpan, step0NormalizeMediaFacts  # noqa: E402


# ── minimal valid news result ────────────────────────────────────────────────

def minimalResult(**overrides):
    base = {
        "source": "impacton",
        "title": "기사 제목",
        "url": "https://example.test/article",
        "publishedAt": "2026-06-11",
        "chunk": "기사 본문 근거 문장",
        "bestSubIssueId": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "bestSubIssueNameKr": "기후변화 대응",
        "bestSimilarityScore": 0.71,
        "issueSimilarityMatches": [],
    }
    base.update(overrides)
    return base


class PhaseC2NewsFactResolverTest(unittest.TestCase):

    # 1. 정상 news result → ExtractedFactsV13 1건
    def test_normal_result_returns_one_fact(self):
        facts = step0NormalizeMediaFacts([minimalResult()])
        self.assertEqual(len(facts), 1)
        self.assertIsInstance(facts[0], ExtractedFactsV13)

    # 2. non-Mapping row → ValueError
    def test_non_mapping_row_raises(self):
        with self.assertRaises(ValueError):
            step0NormalizeMediaFacts(["not_a_dict"])

    # 3. subIssueCode 없음 → ValueError
    def test_missing_sub_issue_code_raises(self):
        row = {"title": "기사", "chunk": "근거", "source": "impacton", "bestSimilarityScore": 0.71}
        with self.assertRaises(ValueError):
            step0NormalizeMediaFacts([row])

    # 3b. subIssueCode 빈 문자열 → ValueError (빈 문자열은 누락으로 처리)
    def test_empty_sub_issue_code_raises(self):
        with self.assertRaises(ValueError):
            step0NormalizeMediaFacts([minimalResult(bestSubIssueId="")])

    # 4. sourceType → ExtractedFactsV13.sourceType == "news"
    def test_source_type_is_news(self):
        facts = step0NormalizeMediaFacts([minimalResult()])
        self.assertEqual(facts[0].sourceType, "news")

    # 5. Evidence sourceType → evidenceSpans[0].sourceType == "news"
    def test_evidence_span_source_type_is_news(self):
        facts = step0NormalizeMediaFacts([minimalResult()])
        self.assertEqual(len(facts[0].evidenceSpans), 1)
        self.assertEqual(facts[0].evidenceSpans[0].sourceType, "news")

    # 6. Provider metadata
    def test_provider_metadata_impacton(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="impacton")])
        md = facts[0].rawMetadata
        self.assertEqual(md["mediaExternalSourceType"], "news")
        self.assertEqual(md["providerKey"], "impacton")

    def test_provider_metadata_esgeconomy(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="esgeconomy")])
        self.assertEqual(facts[0].rawMetadata["providerKey"], "esgeconomy")

    # 7. Backward-compatible source metadata → rawMetadata.source 유지
    def test_backward_compatible_source_field_preserved(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="impacton")])
        self.assertEqual(facts[0].rawMetadata["source"], "impacton")

    # 8. teCrawlingId passthrough
    def test_te_crawling_id_passthrough(self):
        row = minimalResult(teCrawlingId=12345)
        facts = step0NormalizeMediaFacts([row])
        self.assertEqual(facts[0].evidenceSpans[0].teCrawlingId, 12345)

    def test_te_crawling_id_none_when_absent(self):
        facts = step0NormalizeMediaFacts([minimalResult()])
        self.assertIsNone(facts[0].evidenceSpans[0].teCrawlingId)

    # 9. similarity score 의미 → classificationConfidence에만 반영
    def test_similarity_score_maps_only_to_classification_confidence(self):
        facts = step0NormalizeMediaFacts([minimalResult(bestSimilarityScore=0.71)])
        self.assertAlmostEqual(facts[0].classificationConfidence, 0.71)
        dumped = facts[0].model_dump(mode="json", by_alias=False)
        for forbidden_score in ("impactScore", "financialScore", "impactScore05", "financialScore05", "finalScore"):
            self.assertNotIn(forbidden_score, dumped)

    # 10. event fact passthrough — upstream 제공값 DTO에 보존
    def test_event_fact_passthrough_when_provided(self):
        row = minimalResult(
            eventType="disclosure",
            impactDirection="negative",
            financialIroType="risk",
            actualYn="TRUE",
            officialConfirmedYn="FALSE",
            explicitImmediateActionYn="UNKNOWN",
            explicitNoUrgencyYn="FALSE",
            affectedCount=500,
            financialAmount=1000000.0,
            ratioValue=0.05,
            probabilityValue=0.3,
            eventDate="2026-06-01",
            effectiveDate="2026-07-01",
            deadlineDate="2026-12-31",
            eventGroupCandidateId="EVT-001",
        )
        facts = step0NormalizeMediaFacts([row])
        f = facts[0]
        self.assertEqual(f.eventType, "disclosure")
        self.assertEqual(f.impactDirection, "negative")
        self.assertEqual(f.financialIroType, "risk")
        self.assertEqual(f.actualYn.value, "TRUE")
        self.assertEqual(f.officialConfirmedYn.value, "FALSE")
        self.assertEqual(f.explicitImmediateActionYn.value, "UNKNOWN")
        self.assertEqual(f.explicitNoUrgencyYn.value, "FALSE")
        self.assertEqual(f.affectedCount, 500)
        self.assertAlmostEqual(f.financialAmount, 1000000.0)
        self.assertAlmostEqual(f.ratioValue, 0.05)
        self.assertAlmostEqual(f.probabilityValue, 0.3)
        self.assertEqual(f.eventDate, "2026-06-01")
        self.assertEqual(f.effectiveDate, "2026-07-01")
        self.assertEqual(f.deadlineDate, "2026-12-31")
        self.assertEqual(f.eventGroupCandidateId, "EVT-001")

    # 11. event fact no-guess — upstream 미제공 시 None 유지
    def test_event_fact_none_when_not_provided(self):
        facts = step0NormalizeMediaFacts([minimalResult()])
        f = facts[0]
        self.assertIsNone(f.eventType)
        self.assertIsNone(f.impactDirection)
        self.assertIsNone(f.financialIroType)
        self.assertIsNone(f.actualYn)
        self.assertIsNone(f.officialConfirmedYn)
        self.assertIsNone(f.explicitImmediateActionYn)
        self.assertIsNone(f.explicitNoUrgencyYn)
        self.assertIsNone(f.affectedCount)
        self.assertIsNone(f.financialAmount)
        self.assertIsNone(f.ratioValue)
        self.assertIsNone(f.probabilityValue)
        self.assertIsNone(f.eventDate)
        self.assertIsNone(f.effectiveDate)
        self.assertIsNone(f.deadlineDate)
        self.assertIsNone(f.eventGroupCandidateId)

    # 12. forbidden score/factor contamination 방지
    def test_forbidden_score_and_factor_not_in_dto_or_metadata(self):
        row = minimalResult()
        # upstream이 임의 score를 포함해도
        row["impactScore"] = 4.5
        row["financialScore"] = 3.0
        row["impactFactor"] = {"scale": 5}
        row["financialFactor"] = {"magnitude": 3}
        # Pydantic extra="forbid" 이므로 ExtractedFactsV13 생성 자체는 통과
        # (adapter는 명시적 필드만 전달하므로 forbidden 필드는 무시됨)
        facts = step0NormalizeMediaFacts([row])
        dumped = facts[0].model_dump(mode="json", by_alias=False)
        for forbidden in ("impactScore", "financialScore", "impactFactor", "financialFactor",
                          "impactScore05", "financialScore05", "finalScore", "scale", "magnitude"):
            self.assertNotIn(forbidden, dumped)
            self.assertNotIn(forbidden, dumped.get("rawMetadata", {}))

    # 13. provider 누락 → providerKey == "unknown"
    def test_missing_provider_falls_back_to_unknown(self):
        row = {k: v for k, v in minimalResult().items() if k != "source"}
        facts = step0NormalizeMediaFacts([row])
        self.assertEqual(facts[0].rawMetadata["providerKey"], "unknown")

    def test_empty_source_falls_back_to_unknown(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="")])
        self.assertEqual(facts[0].rawMetadata["providerKey"], "unknown")

    # 14. agency/regulation 자동 승격 금지
    def test_kcgs_like_source_stays_news_source_type(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="kcgs")])
        self.assertEqual(facts[0].sourceType, "news")
        self.assertEqual(facts[0].rawMetadata["mediaExternalSourceType"], "news")

    def test_csrd_like_source_stays_news_source_type(self):
        facts = step0NormalizeMediaFacts([minimalResult(source="csrd")])
        self.assertEqual(facts[0].sourceType, "news")
        self.assertEqual(facts[0].rawMetadata["mediaExternalSourceType"], "news")

    # 15. manifest capability 유지
    def test_manifest_capability_config_pending(self):
        manifest_path = (
            Path(__file__).resolve().parents[1]
            / "src/resources/dma/v1_3_mvp/manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["capabilities"]["mediaEventCanonicalAdapter"], "CONFIG_PENDING")


class PhaseC2BuildEvidenceSpanTest(unittest.TestCase):

    def test_chunk_preserves_crawling_id_and_provenance(self):
        result = {
            "chunk": "근거 문장",
            "title": "기사 제목",
            "url": "https://example.test",
            "publishedAt": "2026-06-11",
            "teCrawlingId": 99,
        }
        spans = buildEvidenceSpan(result)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].textSpan, "근거 문장")
        self.assertEqual(spans[0].sourceType, "news")
        self.assertEqual(spans[0].teCrawlingId, 99)
        self.assertEqual(spans[0].sourceUrl, "https://example.test")

    def test_no_chunk_returns_empty_list(self):
        self.assertEqual(buildEvidenceSpan({}), [])
        self.assertEqual(buildEvidenceSpan({"title": "제목만"}), [])

    def test_te_crawling_id_alias_te_crawling_id_snake(self):
        spans = buildEvidenceSpan({"chunk": "text", "te_crawling_id": 7})
        self.assertEqual(spans[0].teCrawlingId, 7)


if __name__ == "__main__":
    unittest.main()
