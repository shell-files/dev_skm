-- =====================================================================
-- SKM ESG Onboarding Integrated DDL v5.2 - FKSnake MinOps MariaDB
-- Purpose : 신규 ESG 온보딩/이중중대성/Fact/Rollup/Narrative 테이블 전체 생성 (MinOps 보정)
-- DB      : MariaDB/MySQL compatible
-- Legacy  : 기존 USER, ROLE, USER_ROLE, TOKEN, COMPANY, INVITE, ALARM,
--           SUPPORTING_FILE, ISSUE, ISSUE_DETAIL 등은 절대 ALTER/RENAME/DROP 하지 않음.
-- Note    : Legacy cross-DB FK는 물리 FK로 선언하지 않고 logical FK로만 사용.
-- FK Rule : 참조키 컬럼은 가능한 경우 {referenced_table_name}_id snake_case를 사용.
--           예: ESG_ONBOARDING_CYCLE.id -> esg_onboarding_cycle_id.
-- v5.2   : FKSnake 규칙 유지. ESG_AUDIT_LOG 유지(보고서 문장/문단 단위 감사추적),
--           회사 관계는 지분율 모델이 아닌 롤업 범위 모델로 최소화.
-- =====================================================================

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- 0. 회사 코드/그룹 관계 보조 테이블
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_COMPANY_PROFILE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    company_code VARCHAR(50) NOT NULL COMMENT '시연/ESG 회사코드: A_GROUP/B_SUB_KR/C_SUB_EU/D_SUB_US',
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY' COMMENT 'ENTITY/CONSOLIDATED',
    active_yn TINYINT(1) NULL DEFAULT 1 COMMENT '사용여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_company_profile_company (company_id),
    UNIQUE KEY uk_esg_company_profile_code (company_code),
    KEY idx_esg_company_profile_scope (company_scope_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 회사 코드 최소 매핑';

CREATE TABLE IF NOT EXISTS ESG_COMPANY_ROLLUP_SCOPE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    parent_company_id BIGINT NOT NULL COMMENT '롤업 요청 주체 COMPANY.id logical FK',
    source_company_id BIGINT NOT NULL COMMENT '롤업 포함 원천 회사 COMPANY.id logical FK',
    source_company_code VARCHAR(50) NULL COMMENT 'A_GROUP/B_SUB_KR/C_SUB_EU/D_SUB_US 등',
    rollup_include_yn TINYINT(1) NULL DEFAULT 1 COMMENT '롤업 포함 여부',
    effective_from_year INT NULL COMMENT '적용 시작 보고연도',
    effective_to_year INT NULL COMMENT '적용 종료 보고연도. NULL이면 현재 유효',
    note TEXT NULL COMMENT '롤업 범위 비고',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_scope (parent_company_id, source_company_id, effective_from_year),
    KEY idx_esg_rollup_scope_source (source_company_id),
    KEY idx_esg_rollup_scope_include (parent_company_id, rollup_include_yn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 회사 롤업 범위';

-- ---------------------------------------------------------------------
-- 1. Master: 62개 sub_issue pool + MVP metric/atomic master
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_SUB_ISSUE_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    issue_group_code VARCHAR(80) NOT NULL COMMENT '상위 issue group 코드',
    issue_group_name_kr VARCHAR(200) NULL COMMENT '상위 issue group 한글명',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT 'sub_issue 코드',
    sub_issue_name_kr VARCHAR(300) NOT NULL COMMENT 'sub_issue 한글명',
    sub_issue_name_en VARCHAR(300) NULL COMMENT 'sub_issue 영문명',
    materiality_issue_pool_yn TINYINT(1) NULL DEFAULT 1 COMMENT '이중중대성평가 pool 포함 여부',
    sort_order INT NULL COMMENT '정렬순서',
    active_yn TINYINT(1) NULL DEFAULT 1 COMMENT '사용여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_sub_issue_code (sub_issue_code),
    KEY idx_esg_sub_issue_group (issue_group_code),
    KEY idx_esg_sub_issue_pool (materiality_issue_pool_yn, active_yn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG sub_issue 62개 master';

CREATE TABLE IF NOT EXISTS ESG_METRIC_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    topic_code VARCHAR(50) NULL COMMENT 'G0/E/S/G 또는 MVP topic 코드',
    materiality_topic VARCHAR(200) NULL COMMENT '현대모비스 선정 이슈 또는 경영일반',
    sub_issue_code VARCHAR(120) NULL COMMENT 'ESG_SUB_ISSUE_MASTER.sub_issue_code logical FK',
    owner_metric_id VARCHAR(50) NULL COMMENT '대표 metric_id',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    metric_name_kr VARCHAR(300) NOT NULL COMMENT '지표명',
    metric_description TEXT NULL COMMENT '지표 설명',
    mandatory_context_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'G0 등 항상 포함 context 여부',
    active_yn TINYINT(1) NULL DEFAULT 1 COMMENT '사용여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_metric_id (metric_id),
    KEY idx_esg_metric_sub_issue (sub_issue_code),
    KEY idx_esg_metric_topic (topic_code, materiality_topic)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG metric master';

CREATE TABLE IF NOT EXISTS ESG_ATOMIC_METRIC_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    topic_code VARCHAR(50) NULL COMMENT 'topic 코드',
    materiality_topic VARCHAR(200) NULL COMMENT '주제명',
    sub_issue_code VARCHAR(120) NULL COMMENT 'sub_issue 코드',
    owner_metric_id VARCHAR(50) NULL COMMENT '대표 metric_id',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    metric_name_kr VARCHAR(300) NULL COMMENT 'metric 명',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'atomic_metric_id. 예: E1-06__Q0001',
    atomic_name_kr VARCHAR(300) NOT NULL COMMENT 'atomic 한글명',
    atomic_name_en VARCHAR(300) NULL COMMENT 'atomic 영문명/짧은 설명',
    description TEXT NULL COMMENT '설명',
    data_value_type VARCHAR(20) NOT NULL COMMENT '정성/정량',
    atomic_data_role VARCHAR(30) NOT NULL COMMENT 'INPUT/DERIVED/REFERENCE',
    token_role VARCHAR(20) NULL COMMENT 'Q/QL/EV/EVENT/ROLLUP',
    onboarding_input_yn TINYINT(1) NULL DEFAULT 0 COMMENT '온보딩 직접입력 여부',
    q_token_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'Q token 여부',
    ql_token_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'QL token 여부',
    ev_token_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'EV token 여부',
    event_token_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'event token 여부',
    applicable_company_scope VARCHAR(50) NULL COMMENT 'ALL_COMPANIES/A_GROUP_ONLY 등',
    group_link_type_code VARCHAR(50) NULL COMMENT 'ENTITY_SOURCE/GROUP_POLICY/GROUP_CONSOLIDATED/ENTITY_ONLY',
    rollup_required_yn TINYINT(1) NULL DEFAULT 0 COMMENT '롤업 필요 여부',
    rollup_role VARCHAR(50) NULL COMMENT 'source/result/reference',
    rollup_formula TEXT NULL COMMENT '롤업 설명식',
    source_atomic_metric_ids TEXT NULL COMMENT 'source atomic list ; separated',
    calculation_formula TEXT NULL COMMENT '사람용 계산식',
    calculation_rule_code VARCHAR(100) NULL COMMENT 'ESG_CALCULATION_RULE.calculation_rule_code logical FK',
    reference_source_atomic_metric_id VARCHAR(80) NULL COMMENT '참조 source atomic',
    unit VARCHAR(50) NULL COMMENT '단위',
    evidence_required_yn TINYINT(1) NULL DEFAULT 0 COMMENT '증빙 필요 여부',
    target_db_table VARCHAR(100) NULL COMMENT '논리 적재 대상',
    narrative_template_owner_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'template owner 여부',
    qa_rule TEXT NULL COMMENT 'QA 규칙',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_atomic_metric_id (atomic_metric_id),
    KEY idx_esg_atomic_metric (metric_id),
    KEY idx_esg_atomic_role (atomic_data_role, token_role),
    KEY idx_esg_atomic_rollup (rollup_required_yn, group_link_type_code),
    KEY idx_esg_atomic_calc_rule (calculation_rule_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG atomic metric master';

CREATE TABLE IF NOT EXISTS ESG_SUB_ISSUE_METRIC_MAP (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT 'sub_issue 코드',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    map_scope VARCHAR(30) NOT NULL DEFAULT 'MVP' COMMENT 'MVP/FULL',
    required_yn TINYINT(1) NULL DEFAULT 1 COMMENT '온보딩 필수 여부',
    sort_order INT NULL COMMENT '정렬순서',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_sub_metric_map (sub_issue_code, metric_id, map_scope),
    KEY idx_esg_sub_metric_metric (metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG sub_issue-metric 매핑';

CREATE TABLE IF NOT EXISTS ESG_SUB_ISSUE_ATOMIC_MAP (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT 'sub_issue 코드',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'atomic_metric_id',
    map_scope VARCHAR(30) NOT NULL DEFAULT 'MVP' COMMENT 'MVP/FULL',
    required_yn TINYINT(1) NULL DEFAULT 1 COMMENT '온보딩 필수 여부',
    sort_order INT NULL COMMENT '정렬순서',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_sub_atomic_map (sub_issue_code, metric_id, atomic_metric_id, map_scope),
    KEY idx_esg_sub_atomic_metric (metric_id),
    KEY idx_esg_sub_atomic_atomic (atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG sub_issue-atomic 매핑';

-- ---------------------------------------------------------------------
-- 2. 이중중대성평가 실행/점수/선정/온보딩 scope
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_MATERIALITY_RUN (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    run_name VARCHAR(200) NOT NULL COMMENT '이중중대성평가 실행명',
    run_status VARCHAR(30) NOT NULL DEFAULT 'draft' COMMENT 'draft/running/scored/selected/closed',
    selected_result_fixed_yn TINYINT(1) NULL DEFAULT 0 COMMENT 'MVP 고정 선정결과 여부',
    requested_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_materiality_company (company_id, reporting_year),
    KEY idx_esg_materiality_status (run_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 이중중대성평가 실행';

CREATE TABLE IF NOT EXISTS ESG_MATERIALITY_SUB_ISSUE_SCORE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_materiality_run_id BIGINT NOT NULL COMMENT 'ESG_MATERIALITY_RUN.id',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT 'sub_issue 코드',
    impact_score DECIMAL(10,4) NULL COMMENT 'impact 점수',
    financial_score DECIMAL(10,4) NULL COMMENT 'financial 점수',
    stakeholder_score DECIMAL(10,4) NULL COMMENT 'stakeholder 점수',
    benchmark_score DECIMAL(10,4) NULL COMMENT 'benchmark 점수',
    media_score DECIMAL(10,4) NULL COMMENT 'media 점수',
    final_score DECIMAL(10,4) NULL COMMENT '최종 점수',
    rank_no INT NULL COMMENT '순위',
    selected_yn TINYINT(1) NULL DEFAULT 0 COMMENT '선정 여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_mat_score (esg_materiality_run_id, sub_issue_code),
    KEY idx_esg_mat_score_selected (esg_materiality_run_id, selected_yn),
    KEY idx_esg_mat_score_rank (esg_materiality_run_id, rank_no),
    CONSTRAINT fk_esg_mat_score_run FOREIGN KEY (esg_materiality_run_id) REFERENCES ESG_MATERIALITY_RUN(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG sub_issue별 이중중대성 점수';

CREATE TABLE IF NOT EXISTS ESG_MATERIALITY_SELECTED_SUB_ISSUE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_materiality_run_id BIGINT NOT NULL COMMENT 'ESG_MATERIALITY_RUN.id',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT '선정 sub_issue 코드',
    selection_type VARCHAR(30) NOT NULL DEFAULT 'mvp_fixed' COMMENT 'mvp_fixed/score_based/manual',
    selected_rank_no INT NULL COMMENT '선정 순위',
    selected_reason TEXT NULL COMMENT '선정 사유',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_selected_sub_issue (esg_materiality_run_id, sub_issue_code),
    KEY idx_esg_selected_sub_run (esg_materiality_run_id),
    CONSTRAINT fk_esg_selected_run FOREIGN KEY (esg_materiality_run_id) REFERENCES ESG_MATERIALITY_RUN(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 최종 선정 sub_issue';

CREATE TABLE IF NOT EXISTS ESG_SELECTED_ONBOARDING_SCOPE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_materiality_selected_sub_issue_id BIGINT NOT NULL COMMENT 'ESG_MATERIALITY_SELECTED_SUB_ISSUE.id',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT 'sub_issue 코드',
    scope_row_type VARCHAR(30) NOT NULL COMMENT 'metric/atomic/mandatory_context',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    atomic_metric_id VARCHAR(80) NULL COMMENT 'atomic_metric_id',
    scope_key VARCHAR(255) NOT NULL COMMENT '중복 방지용 key',
    required_yn TINYINT(1) NULL DEFAULT 1 COMMENT '필수 입력 여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_selected_scope_key (scope_key),
    KEY idx_esg_selected_scope_selected (esg_materiality_selected_sub_issue_id),
    KEY idx_esg_selected_scope_metric (metric_id),
    KEY idx_esg_selected_scope_atomic (atomic_metric_id),
    CONSTRAINT fk_esg_scope_selected FOREIGN KEY (esg_materiality_selected_sub_issue_id) REFERENCES ESG_MATERIALITY_SELECTED_SUB_ISSUE(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 선정 sub_issue별 온보딩 제시 scope 스냅샷';

-- ---------------------------------------------------------------------
-- 3. 온보딩 cycle / 담당자 배정 / 입력 / 제출 / 승인
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_CYCLE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    cycle_name VARCHAR(200) NOT NULL COMMENT '사이클명',
    cycle_status VARCHAR(30) NOT NULL DEFAULT 'open' COMMENT 'open/collecting/review/closed',
    esg_materiality_run_id BIGINT NULL COMMENT 'ESG_MATERIALITY_RUN.id',
    created_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_cycle (company_id, reporting_year),
    KEY idx_esg_cycle_status (cycle_status),
    KEY idx_esg_cycle_materiality (esg_materiality_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 온보딩 사이클';

CREATE TABLE IF NOT EXISTS ESG_METRIC_ASSIGNMENT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_onboarding_cycle_id BIGINT NOT NULL COMMENT 'ESG_ONBOARDING_CYCLE.id',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    invite_id BIGINT NULL COMMENT 'INVITE.id logical FK. 초대 전/중 연결',
    assignee_user_id BIGINT NULL COMMENT 'USER.id logical FK. 초대 수락 후',
    assignee_email VARCHAR(100) NULL COMMENT '초대 이메일. 초대 수락 전 담당자 식별',
    assignment_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending/accepted/in_progress/submitted/completed/canceled',
    due_date DATE NULL COMMENT '제출기한',
    created_by_user_id BIGINT NULL COMMENT '배정자 USER.id logical FK',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_assignment_cycle (esg_onboarding_cycle_id),
    KEY idx_esg_assignment_company (company_id),
    KEY idx_esg_assignment_metric (metric_id),
    KEY idx_esg_assignment_user (assignee_user_id),
    KEY idx_esg_assignment_email (assignee_email),
    CONSTRAINT fk_esg_assignment_cycle FOREIGN KEY (esg_onboarding_cycle_id) REFERENCES ESG_ONBOARDING_CYCLE(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG metric 담당자 배정';

CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_INPUT_VALUE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_metric_assignment_id BIGINT NULL COMMENT 'ESG_METRIC_ASSIGNMENT.id',
    esg_onboarding_cycle_id BIGINT NULL COMMENT 'ESG_ONBOARDING_CYCLE.id',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY' COMMENT 'ENTITY. CONSOLIDATED는 롤업결과 테이블에서 관리',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'atomic_metric_id',
    value_numeric DECIMAL(24,6) NULL COMMENT '정량값',
    value_text LONGTEXT NULL COMMENT '정성값',
    unit VARCHAR(50) NULL COMMENT '단위',
    value_source_type VARCHAR(30) NULL DEFAULT 'manual_input' COMMENT 'manual_input/calculated/reference_copy/imported',
    input_status VARCHAR(30) NOT NULL DEFAULT 'draft' COMMENT 'draft/submitted/approved/rejected',
    input_user_id BIGINT NULL COMMENT '입력자 USER.id logical FK',
    approved_by_user_id BIGINT NULL COMMENT '승인자 USER.id logical FK',
    approved_at DATETIME NULL COMMENT '승인일시',
    source_file_id BIGINT NULL COMMENT 'SUPPORTING_FILE.id logical FK',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_input (company_id, reporting_year, company_scope_type, atomic_metric_id),
    KEY idx_esg_input_assignment (esg_metric_assignment_id),
    KEY idx_esg_input_cycle (esg_onboarding_cycle_id),
    KEY idx_esg_input_metric (metric_id),
    KEY idx_esg_input_atomic (atomic_metric_id),
    KEY idx_esg_input_status (input_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 온보딩 atomic 입력값';

CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_SUBMISSION (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_onboarding_cycle_id BIGINT NOT NULL COMMENT 'ESG_ONBOARDING_CYCLE.id',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    esg_metric_assignment_id BIGINT NULL COMMENT 'ESG_METRIC_ASSIGNMENT.id',
    submitter_user_id BIGINT NOT NULL COMMENT 'USER.id logical FK',
    submission_status VARCHAR(30) NOT NULL DEFAULT 'submitted' COMMENT 'submitted/under_review/approved/rejected/revision_requested/resubmitted',
    submitted_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '제출일시',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_submission (esg_onboarding_cycle_id, company_id, metric_id),
    KEY idx_esg_submission_cycle (esg_onboarding_cycle_id),
    KEY idx_esg_submission_company (company_id),
    KEY idx_esg_submission_metric (metric_id),
    KEY idx_esg_submission_status (submission_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 온보딩 제출';

CREATE TABLE IF NOT EXISTS ESG_APPROVAL_TASK (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    esg_onboarding_submission_id BIGINT NULL COMMENT 'ESG_ONBOARDING_SUBMISSION.id',
    approver_user_id BIGINT NULL COMMENT '승인자 USER.id logical FK',
    task_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected/revision_requested/canceled',
    comment_text TEXT NULL COMMENT '승인자 코멘트',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_approval_company (company_id, reporting_year),
    KEY idx_esg_approval_metric (metric_id),
    KEY idx_esg_approval_status (task_status),
    CONSTRAINT fk_esg_approval_submission
        FOREIGN KEY (esg_onboarding_submission_id) REFERENCES ESG_ONBOARDING_SUBMISSION(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 승인 작업';

CREATE TABLE IF NOT EXISTS ESG_APPROVAL_LOG (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_approval_task_id BIGINT NOT NULL COMMENT 'ESG_APPROVAL_TASK.id',
    action VARCHAR(30) NOT NULL COMMENT 'submitted/approved/rejected/revision_requested/resubmitted',
    actor_user_id BIGINT NOT NULL COMMENT 'USER.id logical FK',
    comment_text TEXT NULL COMMENT '코멘트',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    PRIMARY KEY (id),
    KEY idx_esg_approval_log_task (esg_approval_task_id),
    KEY idx_esg_approval_log_actor (actor_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 승인 이력';

CREATE TABLE IF NOT EXISTS ESG_AUDIT_LOG (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NULL COMMENT 'COMPANY.id logical FK',
    actor_user_id BIGINT NULL COMMENT 'USER.id logical FK. 시스템 이벤트는 NULL 가능',
    event_type VARCHAR(100) NOT NULL COMMENT '이벤트 유형: input_update/calculation_run/rollup_run/report_generate/reference_link 등',
    target_table VARCHAR(100) NOT NULL COMMENT '대상 테이블',
    target_id BIGINT NULL COMMENT '대상 id',
    draft_id VARCHAR(120) NULL COMMENT '보고서 문단 draft_id. 문장/문단 감사추적 라벨용',
    atomic_metric_id VARCHAR(80) NULL COMMENT '관련 atomic_metric_id',
    reference_type VARCHAR(50) NULL COMMENT 'kpi_fact/rollup_result/evidence_chunk/source_document 등',
    reference_id VARCHAR(120) NULL COMMENT '참조 ID',
    old_value_json LONGTEXT NULL COMMENT '변경 전 JSON',
    new_value_json LONGTEXT NULL COMMENT '변경 후 JSON',
    trace_label_json LONGTEXT NULL COMMENT '보고서 문단/문장 단위 히든 감사 라벨 JSON',
    request_id VARCHAR(100) NULL COMMENT '요청 ID',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    PRIMARY KEY (id),
    KEY idx_esg_audit_company (company_id),
    KEY idx_esg_audit_actor (actor_user_id),
    KEY idx_esg_audit_target (target_table, target_id),
    KEY idx_esg_audit_draft (draft_id),
    KEY idx_esg_audit_atomic (atomic_metric_id),
    CONSTRAINT ck_esg_audit_old_json CHECK (old_value_json IS NULL OR JSON_VALID(old_value_json)),
    CONSTRAINT ck_esg_audit_new_json CHECK (new_value_json IS NULL OR JSON_VALID(new_value_json)),
    CONSTRAINT ck_esg_audit_trace_json CHECK (trace_label_json IS NULL OR JSON_VALID(trace_label_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 감사 로그';

-- ---------------------------------------------------------------------
-- 4. Fact / Calculation / Rollup
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_FACT_CANDIDATE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_onboarding_input_value_id BIGINT NULL COMMENT 'ESG_ONBOARDING_INPUT_VALUE.id',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY' COMMENT 'ENTITY',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'atomic_metric_id',
    value_numeric DECIMAL(24,6) NULL COMMENT '정량값',
    value_text LONGTEXT NULL COMMENT '정성값',
    unit VARCHAR(50) NULL COMMENT '단위',
    value_source_type VARCHAR(30) NULL COMMENT 'manual_input/calculated/reference_copy',
    candidate_status VARCHAR(30) NOT NULL DEFAULT 'submitted' COMMENT 'submitted/approved/rejected',
    created_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    approved_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    approved_at DATETIME NULL COMMENT '승인일시',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_fact_candidate_input (esg_onboarding_input_value_id),
    KEY idx_esg_fact_candidate_company (company_id, reporting_year),
    KEY idx_esg_fact_candidate_atomic (atomic_metric_id),
    KEY idx_esg_fact_candidate_status (candidate_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG fact 후보값';

CREATE TABLE IF NOT EXISTS ESG_KPI_FACT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_fact_candidate_id BIGINT NULL COMMENT 'ESG_FACT_CANDIDATE.id',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY' COMMENT 'ENTITY',
    metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'atomic_metric_id',
    value_numeric DECIMAL(24,6) NULL COMMENT '정량값',
    value_text LONGTEXT NULL COMMENT '정성값',
    unit VARCHAR(50) NULL COMMENT '단위',
    value_source_type VARCHAR(30) NULL COMMENT 'manual_input/calculated/reference_copy',
    approval_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected',
    approved_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    approved_at DATETIME NULL COMMENT '승인일시',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_kpi_fact (company_id, reporting_year, company_scope_type, atomic_metric_id),
    KEY idx_esg_kpi_metric (metric_id),
    KEY idx_esg_kpi_atomic (atomic_metric_id),
    KEY idx_esg_kpi_status (approval_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 승인 확정 KPI fact';

CREATE TABLE IF NOT EXISTS ESG_CALCULATION_RULE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    calculation_rule_code VARCHAR(100) NOT NULL COMMENT '계산 규칙 코드',
    target_atomic_metric_id VARCHAR(80) NOT NULL COMMENT '결과 atomic_metric_id',
    target_atomic_name_kr VARCHAR(300) NULL COMMENT '결과 atomic 명',
    metric_id VARCHAR(50) NULL COMMENT 'metric_id',
    formula_type VARCHAR(50) NOT NULL COMMENT 'REFERENCE_COPY/ENTITY_SUM/ENTITY_RATIO/ENTITY_DIVIDE/ROLLUP_SUM/ROLLUP_RATIO_RECALC/ROLLUP_YOY_DIFF/ROLLUP_YOY_RATE',
    execution_scope VARCHAR(30) NOT NULL COMMENT 'ENTITY/CONSOLIDATED',
    applicable_company_scope VARCHAR(200) NULL COMMENT '적용 회사 범위 설명',
    source_atomic_metric_ids TEXT NULL COMMENT 'source atomic list',
    numerator_atomic_metric_ids TEXT NULL COMMENT 'numerator atomic list',
    denominator_atomic_metric_ids TEXT NULL COMMENT 'denominator atomic list',
    calculation_formula_label TEXT NULL COMMENT '사람용 계산식',
    sql_template LONGTEXT NOT NULL COMMENT 'MariaDB 실행 SQL 템플릿. ? positional parameter 사용',
    zero_division_policy VARCHAR(50) NULL COMMENT '분모 0 처리',
    rounding_policy VARCHAR(50) NULL COMMENT '반올림 정책',
    result_table VARCHAR(100) NULL COMMENT '결과 적재 테이블',
    output_unit VARCHAR(50) NULL COMMENT '출력 단위',
    execution_order INT NULL COMMENT '실행 순서',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_calc_rule_code (calculation_rule_code),
    KEY idx_esg_calc_target (target_atomic_metric_id),
    KEY idx_esg_calc_type (formula_type, execution_scope),
    CONSTRAINT ck_esg_calc_sql_not_empty CHECK (CHAR_LENGTH(sql_template) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 계산 규칙 마스터';

CREATE TABLE IF NOT EXISTS ESG_CALCULATION_RULE_SOURCE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    calculation_rule_code VARCHAR(100) NOT NULL COMMENT 'ESG_CALCULATION_RULE.calculation_rule_code logical FK',
    target_atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'target atomic_metric_id',
    source_atomic_metric_id VARCHAR(80) NOT NULL COMMENT 'source atomic_metric_id',
    source_role VARCHAR(30) NULL COMMENT 'numerator/denominator/addend/source/reference',
    source_scope VARCHAR(30) NULL COMMENT 'ENTITY/CONSOLIDATED',
    source_metric_id VARCHAR(50) NULL COMMENT 'source metric_id',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_calc_source_rule (calculation_rule_code),
    KEY idx_esg_calc_source_target (target_atomic_metric_id),
    KEY idx_esg_calc_source_atomic (source_atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 계산 규칙 소스 매핑';

CREATE TABLE IF NOT EXISTS ESG_ROLLUP_BATCH (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    rollup_batch_code VARCHAR(100) NOT NULL COMMENT '롤업 배치 코드',
    parent_company_id BIGINT NOT NULL COMMENT '그룹사 COMPANY.id logical FK',
    reporting_year INT NOT NULL COMMENT '보고연도',
    batch_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending/processing/completed/failed/approved',
    requested_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    completed_at DATETIME NULL COMMENT '완료일시',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_batch_code (rollup_batch_code),
    KEY idx_esg_rollup_batch_company (parent_company_id, reporting_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 롤업 배치 실행';

CREATE TABLE IF NOT EXISTS ESG_GROUP_ROLLUP_RESULT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_rollup_batch_id BIGINT NOT NULL COMMENT 'ESG_ROLLUP_BATCH.id',
    rollup_result_code VARCHAR(120) NULL COMMENT '롤업 결과 코드',
    reporting_year INT NOT NULL COMMENT '보고연도',
    parent_company_id BIGINT NOT NULL COMMENT '그룹사 COMPANY.id logical FK',
    parent_company_scope_type VARCHAR(30) NOT NULL COMMENT 'CONSOLIDATED',
    included_company_ids TEXT NULL COMMENT '포함 COMPANY.id 목록. ESG_COMPANY_ROLLUP_SCOPE 조회 후 동적 생성. 세미콜론 구분',
    group_metric_id VARCHAR(50) NOT NULL COMMENT 'metric_id',
    group_atomic_metric_id VARCHAR(80) NOT NULL COMMENT '그룹 결과 atomic_metric_id',
    group_atomic_name VARCHAR(300) NULL COMMENT '그룹 결과 atomic 명',
    value_numeric DECIMAL(24,6) NULL COMMENT '롤업 결과 정량값',
    value_text LONGTEXT NULL COMMENT '롤업 결과 정성값',
    unit VARCHAR(50) NULL COMMENT '단위',
    source_company_values_json LONGTEXT NULL COMMENT '회사별 원본값 JSON',
    rollup_method VARCHAR(50) NULL COMMENT 'SUM/REFERENCE/RECALCULATE/YOY_DIFF/YOY_RATE',
    calculation_trace TEXT NULL COMMENT '계산 추적 설명',
    rollup_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected',
    approved_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    approved_at DATETIME NULL COMMENT '승인일시',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_result (esg_rollup_batch_id, group_atomic_metric_id),
    KEY idx_esg_rollup_result_parent (parent_company_id, parent_company_scope_type, reporting_year),
    KEY idx_esg_rollup_result_metric (group_metric_id, group_atomic_metric_id),
    CONSTRAINT ck_esg_rollup_json CHECK (source_company_values_json IS NULL OR JSON_VALID(source_company_values_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 그룹 롤업 결과';

-- ---------------------------------------------------------------------
-- 5. Evidence / Narrative / Report
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ESG_SOURCE_DOCUMENT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    source_document_id VARCHAR(100) NOT NULL COMMENT '문서 ID. 예: DOC-E1-001',
    company_id BIGINT NULL COMMENT 'COMPANY.id logical FK',
    supporting_file_id BIGINT NULL COMMENT 'SUPPORTING_FILE.id logical FK',
    source_document_title VARCHAR(300) NOT NULL COMMENT '문서명',
    document_type VARCHAR(50) NULL COMMENT 'policy/procedure/evidence/report',
    owner_metric_id VARCHAR(50) NULL COMMENT '관련 owner_metric_id',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_source_document_id (source_document_id),
    KEY idx_esg_source_company (company_id),
    KEY idx_esg_source_file (supporting_file_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG source document';

CREATE TABLE IF NOT EXISTS ESG_EVIDENCE_CHUNK (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    evidence_chunk_id VARCHAR(100) NOT NULL COMMENT 'chunk ID',
    source_document_id VARCHAR(100) NOT NULL COMMENT 'ESG_SOURCE_DOCUMENT.source_document_id logical FK',
    section_title VARCHAR(300) NULL COMMENT '섹션명',
    page_no INT NULL COMMENT '페이지',
    quote_summary TEXT NULL COMMENT '근거 요약',
    evidence_role VARCHAR(80) NULL COMMENT 'policy_evidence/evidence_summary/cap_evidence 등',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_evidence_chunk_id (evidence_chunk_id),
    KEY idx_esg_evidence_source (source_document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG evidence chunk';

CREATE TABLE IF NOT EXISTS ESG_NARRATIVE_TEMPLATE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    narrative_template_id VARCHAR(100) NOT NULL COMMENT 'template ID',
    owner_metric_id VARCHAR(50) NOT NULL COMMENT '대표 metric_id',
    owner_metric_name VARCHAR(300) NULL COMMENT '대표 metric 명',
    materiality_topic VARCHAR(200) NULL COMMENT '주제명',
    sub_issue_code VARCHAR(120) NULL COMMENT 'sub_issue 코드',
    related_metric_ids TEXT NULL COMMENT '관련 metric_id 목록',
    template_text_with_atomic_tokens LONGTEXT NOT NULL COMMENT 'atomic token 기반 템플릿',
    expected_output_structure TEXT NULL COMMENT '출력 구조',
    report_section_hint VARCHAR(200) NULL COMMENT '보고서 섹션 힌트',
    template_status VARCHAR(30) NULL DEFAULT 'active' COMMENT 'active/inactive',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_template_id (narrative_template_id),
    KEY idx_esg_template_owner_metric (owner_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG narrative template';

CREATE TABLE IF NOT EXISTS ESG_NARRATIVE_TEMPLATE_TOKEN (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    narrative_template_id VARCHAR(100) NOT NULL COMMENT 'ESG_NARRATIVE_TEMPLATE.narrative_template_id logical FK',
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT '토큰 atomic_metric_id',
    token_role VARCHAR(20) NULL COMMENT 'Q/QL/EV/ROLLUP',
    required_yn TINYINT(1) NULL DEFAULT 1 COMMENT '필수 여부',
    sort_order INT NULL COMMENT '정렬순서',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_template_token (narrative_template_id, atomic_metric_id),
    KEY idx_esg_template_token_atomic (atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG narrative template token';

CREATE TABLE IF NOT EXISTS ESG_REPORT_CONTEXT_SNAPSHOT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    context_snapshot_id VARCHAR(120) NOT NULL COMMENT 'context snapshot ID',
    reporting_year INT NOT NULL COMMENT '보고연도',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    company_scope_type VARCHAR(30) NOT NULL COMMENT 'ENTITY/CONSOLIDATED',
    narrative_template_id VARCHAR(100) NOT NULL COMMENT 'template ID',
    q_context_json LONGTEXT NULL COMMENT 'Q context JSON',
    ql_context_json LONGTEXT NULL COMMENT 'QL context JSON',
    ev_context_json LONGTEXT NULL COMMENT 'EV context JSON',
    rollup_context_json LONGTEXT NULL COMMENT 'rollup context JSON',
    source_context_hash VARCHAR(128) NULL COMMENT 'context hash',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_context_snapshot (context_snapshot_id),
    KEY idx_esg_context_company (company_id, reporting_year),
    CONSTRAINT ck_esg_context_q_json CHECK (q_context_json IS NULL OR JSON_VALID(q_context_json)),
    CONSTRAINT ck_esg_context_ql_json CHECK (ql_context_json IS NULL OR JSON_VALID(ql_context_json)),
    CONSTRAINT ck_esg_context_ev_json CHECK (ev_context_json IS NULL OR JSON_VALID(ev_context_json)),
    CONSTRAINT ck_esg_context_rollup_json CHECK (rollup_context_json IS NULL OR JSON_VALID(rollup_context_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG report context snapshot';

CREATE TABLE IF NOT EXISTS ESG_REPORT_SECTION_DRAFT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    draft_id VARCHAR(120) NOT NULL COMMENT 'draft ID',
    reporting_year INT NOT NULL COMMENT '보고연도',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    company_scope_type VARCHAR(30) NOT NULL COMMENT 'ENTITY/CONSOLIDATED',
    materiality_topic VARCHAR(200) NULL COMMENT '주제명',
    sub_issue_code VARCHAR(120) NULL COMMENT 'sub_issue 코드',
    owner_metric_id VARCHAR(50) NULL COMMENT 'owner metric_id',
    narrative_template_id VARCHAR(100) NULL COMMENT 'template ID',
    internal_management_summary LONGTEXT NULL COMMENT '내부 관리용 설명',
    report_narrative_draft LONGTEXT NOT NULL COMMENT '보고서 문단 초안',
    used_q_atomic_ids TEXT NULL COMMENT '사용 Q atomic 목록',
    used_ql_atomic_ids TEXT NULL COMMENT '사용 QL atomic 목록',
    used_ev_atomic_ids TEXT NULL COMMENT '사용 EV atomic 목록',
    used_rollup_atomic_ids TEXT NULL COMMENT '사용 rollup atomic 목록',
    qa_score DECIMAL(5,2) NULL COMMENT 'QA 점수',
    qa_status VARCHAR(30) NULL COMMENT 'PASS/REVIEW/FAIL',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_report_draft_id (draft_id),
    KEY idx_esg_report_company (company_id, reporting_year),
    KEY idx_esg_report_template (narrative_template_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG 보고서 문단 초안';

CREATE TABLE IF NOT EXISTS ESG_NARRATIVE_REFERENCE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    draft_id VARCHAR(120) NOT NULL COMMENT 'ESG_REPORT_SECTION_DRAFT.draft_id logical FK',
    reference_type VARCHAR(50) NOT NULL COMMENT 'kpi_fact/rollup_result/evidence_chunk/source_document',
    reference_id VARCHAR(120) NOT NULL COMMENT '참조 ID',
    atomic_metric_id VARCHAR(80) NULL COMMENT '관련 atomic_metric_id',
    source_document_id VARCHAR(100) NULL COMMENT 'source document ID',
    evidence_chunk_id VARCHAR(100) NULL COMMENT 'evidence chunk ID',
    quote_summary TEXT NULL COMMENT '인용/근거 요약',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
    delete_yn TINYINT(1) NULL DEFAULT 0 COMMENT '삭제여부',
    PRIMARY KEY (id),
    KEY idx_esg_narr_ref_draft (draft_id),
    KEY idx_esg_narr_ref_atomic (atomic_metric_id),
    KEY idx_esg_narr_ref_type (reference_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG narrative reference';

CREATE TABLE IF NOT EXISTS ESG_SEED_QA_RESULT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    seed_version VARCHAR(50) NOT NULL COMMENT 'seed version',
    qa_item VARCHAR(200) NOT NULL COMMENT 'QA 항목',
    qa_status VARCHAR(30) NOT NULL COMMENT 'PASS/FAIL/REVIEW',
    qa_detail TEXT NULL COMMENT '상세',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일자',
    PRIMARY KEY (id),
    KEY idx_esg_seed_qa_version (seed_version, qa_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ESG seed QA 결과';
