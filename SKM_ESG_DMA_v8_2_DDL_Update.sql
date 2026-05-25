-- =========================================================
-- DMA v8.2 아키텍처 확장에 따른 신규 Audit/Ledger 테이블 4종
-- 기존 ESG_MATERIALITY_RUN 및 SUMMARY 테이블 구조와 연동
-- =========================================================

-- 1. 기업 컨텍스트 보정기록 테이블
CREATE TABLE ESG_DMA_CONTEXT_PROFILE (
    esg_dma_context_profile_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    industry_profile VARCHAR(100) NOT NULL,
    business_model VARCHAR(255) NULL,
    context_json JSON NOT NULL,
    modifier_json JSON NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. 텍스트 분석 상세 원장(Ledger) 테이블 (유사도 및 Rule-based 점수)
CREATE TABLE ESG_DMA_SCORE_DETAIL (
    esg_dma_score_detail_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    sub_issue_code VARCHAR(100) NOT NULL,
    source_step VARCHAR(50) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    iro_type VARCHAR(50) NOT NULL,
    time_horizon VARCHAR(20) NOT NULL,
    issue_similarity_score DECIMAL(8,4) NULL,
    similarity_rank INT NULL,
    similarity_threshold DECIMAL(8,4) NULL,
    mapping_weight DECIMAL(10,6) NULL,
    mapping_method VARCHAR(50) NULL,
    matched_dictionary_terms JSON NULL,
    impact_scale TINYINT NULL,
    impact_scope TINYINT NULL,
    impact_irremediability TINYINT NULL,
    impact_likelihood TINYINT NULL,
    financial_revenue TINYINT NULL,
    financial_cost TINYINT NULL,
    financial_capex TINYINT NULL,
    financial_asset_liability TINYINT NULL,
    financial_financing TINYINT NULL,
    financial_legal_regulatory TINYINT NULL,
    financial_likelihood TINYINT NULL,
    impact_score DECIMAL(8,4) NULL,
    financial_score DECIMAL(8,4) NULL,
    confidence_score DECIMAL(8,4) NULL,
    evidence_id BIGINT NULL,
    scoring_rule_version VARCHAR(100) NOT NULL,
    judge_status VARCHAR(20) NOT NULL,
    judge_reason TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. 뉴스/보고서 근거 문구(Evidence) 추적 테이블
CREATE TABLE ESG_DMA_EVIDENCE (
    evidence_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_type VARCHAR(100) NOT NULL,
    source_title VARCHAR(500) NULL,
    source_url TEXT NULL,
    source_document_id BIGINT NULL,
    page_no INT NULL,
    text_span TEXT NOT NULL,
    event_group_id VARCHAR(100) NULL,
    source_published_at DATETIME NULL,
    source_credibility_score DECIMAL(8,4) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. 이해관계자 설문 응답 상세 테이블
CREATE TABLE ESG_DMA_SURVEY_RESPONSE (
    esg_dma_survey_response_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    respondent_group VARCHAR(50) NOT NULL,
    department_code VARCHAR(100) NULL,
    sub_issue_code VARCHAR(100) NULL,
    question_id VARCHAR(100) NOT NULL,
    answer_value DECIMAL(8,4) NOT NULL,
    normalized_score DECIMAL(8,4) NOT NULL,
    mapped_axis VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
