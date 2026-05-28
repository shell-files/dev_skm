/* =====================================================================
   SKM ESG v5.2 CLEAN_SCHEMA_v2 ONBOARDING ONLY SEED - company6789
   목적:
     - CLEAN_SCHEMA_v2 기준 온보딩/Fact/계산/롤업 더미만 적재
     - DMA 점수, 설문, 미디어, 보고서 draft는 적재하지 않음
   전제:
     - with.USER / skm.COMPANY의 company_id 6/7/8/9는 사전에 존재
     - COMPANY/USER 개인정보성 컬럼은 기존 서비스 방식(aes_e/aes_d)으로 관리
   ===================================================================== */
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET collation_connection = 'utf8mb4_unicode_ci';

SET @user_id_esg_admin := COALESCE((SELECT id FROM `with`.`USER` WHERE delete_yn = 0 ORDER BY id LIMIT 1), 1);
-- 필요 시 아래 값을 실제 관리자 USER.id로 직접 수정한다.
SET @user_id_assignee := COALESCE((SELECT id FROM `with`.`USER` ORDER BY id LIMIT 1), @user_id_esg_admin);
SET @user_id_approver := @user_id_esg_admin;

SET @company_id_A_GROUP := 6;
SET @company_id_B_SUB_KR := 7;
SET @company_id_C_SUB_EU := 8;
SET @company_id_D_SUB_US := 9;

START TRANSACTION;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- 0. Master seed: 62 sub_issue / 18 metric / 179 atomic / sub_issue atomic map
-- ---------------------------------------------------------------------
INSERT INTO ESG_SUB_ISSUE_MASTER (issue_group_code, issue_group_name_kr, sub_issue_code, sub_issue_name_kr, sub_issue_name_en, materiality_issue_pool_yn, sort_order, active_yn) VALUES
    ('E_CLIMATE', '기후변화·온실가스', 'E_CLIMATE__CLIMATE_GOVERNANCE_INVENTORY', '기후 거버넌스·인벤토리', 'Climate governance and
GHG accounting', 1, 1, 1),
    ('E_CLIMATE', '기후변화·온실가스', 'E_CLIMATE__CLIMATE_RISK', '기후 리스크', 'Climate risks', 1, 2, 1),
    ('E_CLIMATE', '기후변화·온실가스', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', '기후목표·전환계획', 'Climate targets and transition plan', 1, 3, 1),
    ('E_CLIMATE', '기후변화·온실가스', 'E_CLIMATE__GHG_SCOPE12_EMISSIONS', 'Scope 1·2 GHG 배출', 'Scope 1 and 2 GHG emissions', 1, 4, 1),
    ('E_CLIMATE', '기후변화·온실가스', 'E_CLIMATE__SCOPE3_VALUE_CHAIN_EMISSIONS', 'Scope 3·가치사슬 배출', 'Scope 3 and value-chain emissions', 1, 5, 1),
    ('E_ENERGY', '에너지', 'E_ENERGY__ENERGY_EFFICIENCY', '에너지 효율·집약도', 'Energy efficiency and intensity', 1, 6, 1),
    ('E_ENERGY', '에너지', 'E_ENERGY__ENERGY_USE_MIX', '에너지 사용·에너지원', 'Energy use and energy mix', 1, 7, 1),
    ('E_ENERGY', '에너지', 'E_ENERGY__RENEWABLE_ENERGY', '재생에너지', 'Renewable energy', 1, 8, 1),
    ('E_WATER', '수자원·폐수', 'E_WATER__WASTEWATER_QUALITY', '폐수·수질오염물질', 'Wastewater and water pollutants', 1, 9, 1),
    ('E_WATER', '수자원·폐수', 'E_WATER__WATER_REUSE_RISK', '용수 재이용·물 리스크', 'Water reuse and water risk', 1, 10, 1),
    ('E_WATER', '수자원·폐수', 'E_WATER__WATER_USE_WITHDRAWAL', '용수 사용·취수', 'Water use and withdrawal', 1, 11, 1),
    ('E_POLLUTION', '오염·유해물질', 'E_POLLUTION__AIR_EMISSIONS', '대기오염물질', 'Air emissions', 1, 12, 1),
    ('E_POLLUTION', '오염·유해물질', 'E_POLLUTION__HAZARDOUS_SUBSTANCES', '유해화학물질·오염물질 관리', 'Hazardous substances and pollutants', 1, 13, 1),
    ('E_POLLUTION', '오염·유해물질', 'E_POLLUTION__POLLUTION_INCIDENTS_COMPLIANCE', '환경사고·오염 법규위반', 'Pollution incidents and environmental compliance', 1, 14, 1),
    ('E_CIRCULARITY', '자원순환·폐기물', 'E_CIRCULARITY__CIRCULAR_MATERIALS', '원재료·순환자원', 'Raw materials and circular materials', 1, 15, 1),
    ('E_CIRCULARITY', '자원순환·폐기물', 'E_CIRCULARITY__RECYCLING_RECOVERY', '재활용·회수', 'Recycling and recovery', 1, 16, 1),
    ('E_CIRCULARITY', '자원순환·폐기물', 'E_CIRCULARITY__WASTE_MANAGEMENT', '폐기물 관리', 'Waste management', 1, 17, 1),
    ('E_BIODIVERSITY', '생물다양성', 'E_BIODIVERSITY__BIODIVERSITY_IMPACTS', '생물다양성 영향', 'Biodiversity impacts', 1, 18, 1),
    ('E_BIODIVERSITY', '생물다양성', 'E_BIODIVERSITY__RESTORATION_CONSERVATION', '복원·보전', 'Restoration and conservation', 1, 19, 1),
    ('E_PRODUCT_ENV', '제품 환경성', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', '저탄소·친환경 제품', 'Eco-friendly products and environmental performance', 1, 20, 1),
    ('E_PRODUCT_ENV', '제품 환경성', 'E_PRODUCT_ENV__PRODUCT_LCA_CERTIFICATION', '제품 환경성과·LCA', 'Product LCA and environmental certification', 1, 21, 1),
    ('E_SUPPLY_CHAIN_ENV', '공급망 환경', 'E_SUPPLY_CHAIN_ENV__SUPPLIER_ENV_ASSESSMENT', '공급망 환경평가', 'Supplier environmental assessment', 1, 22, 1),
    ('E_SUSTAINABLE_INVESTMENT', '지속가능 투자·R&D', 'E_SUSTAINABLE_INVESTMENT__GREEN_PROCUREMENT', '녹색조달·친환경 구매', 'Green procurement', 1, 23, 1),
    ('E_SUSTAINABLE_INVESTMENT', '지속가능 투자·R&D', 'E_SUSTAINABLE_INVESTMENT__SUSTAINABLE_RND_CAPEX', '지속가능 R&D·CAPEX', 'Sustainable R&D and CAPEX', 1, 24, 1),
    ('S_LABOR', '고용·근로조건', 'S_LABOR__HIRING_TURNOVER_RETENTION', '채용·이직·유지', 'Hiring, turnover and retention', 1, 25, 1),
    ('S_LABOR', '고용·근로조건', 'S_LABOR__WORKFORCE_COMPOSITION', '고용·인력 구성', 'Employment and workforce composition', 1, 26, 1),
    ('S_LABOR', '고용·근로조건', 'S_LABOR__WORKING_CONDITIONS_LABOR_RELATIONS', '근로조건·노사관계', 'Working conditions and labor relations', 1, 27, 1),
    ('S_SAFETY', '안전보건', 'S_SAFETY__OHS_MANAGEMENT', '안전보건 관리체계', 'Occupational health and safety management', 1, 28, 1),
    ('S_SAFETY', '안전보건', 'S_SAFETY__SAFETY_TRAINING_HIGH_RISK_WORK', '안전교육·고위험작업', 'Safety training and high-risk work', 1, 29, 1),
    ('S_SAFETY', '안전보건', 'S_SAFETY__SEVERE_ACCIDENT_FATALITY', '중대재해·사망사고', 'Severe accidents and fatalities', 1, 30, 1),
    ('S_TALENT', '교육·인재개발', 'S_TALENT__PERFORMANCE_CAREER', '성과평가·경력개발', 'Performance and career development', 1, 31, 1),
    ('S_TALENT', '교육·인재개발', 'S_TALENT__TRAINING_DEVELOPMENT', '교육훈련·역량개발', 'Training and development', 1, 32, 1),
    ('S_DIVERSITY', '다양성·포용', 'S_DIVERSITY__DISCRIMINATION_HARASSMENT', '차별·괴롭힘 사건', 'Discrimination and harassment', 1, 33, 1),
    ('S_DIVERSITY', '다양성·포용', 'S_DIVERSITY__DIVERSITY_INCLUSION', '다양성·포용 정책', 'Diversity and inclusion', 1, 34, 1),
    ('S_DIVERSITY', '다양성·포용', 'S_DIVERSITY__GENDER_EQUITY', '성별 다양성·형평성', 'Gender diversity and equity', 1, 35, 1),
    ('S_HUMAN_RIGHTS', '인권·고충처리', 'S_HUMAN_RIGHTS__GRIEVANCE_REMEDY', '고충처리·구제', 'Grievance and remedy', 1, 36, 1),
    ('S_SUPPLY_CHAIN_SOCIAL', '공급망 사회', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_CODE_DUE_DILIGENCE', '가치사슬 근로자 인권·실사', 'Supplier code and due diligence', 1, 37, 1),
    ('S_SUPPLY_CHAIN_SOCIAL', '공급망 사회', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_GRIEVANCE_VIOLATIONS', '공급망 고충·중대위반', 'Supplier violations and grievance', 1, 38, 1),
    ('S_SUPPLY_CHAIN_SOCIAL', '공급망 사회', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', '공급망 감사·시정조치', 'Supplier risk, audit and CAP', 1, 39, 1),
    ('S_COMMUNITY', '지역사회', 'S_COMMUNITY__COMMUNITY_IMPACT_ENGAGEMENT', '영향받는 지역사회 영향·참여', 'Community impact and engagement', 1, 40, 1),
    ('S_COMMUNITY', '지역사회', 'S_COMMUNITY__SOCIAL_CONTRIBUTION_INVESTMENT', '사회공헌·투자', 'Social contribution and investment', 1, 41, 1),
    ('S_PRODUCT_RESP', '제품책임·고객', 'S_PRODUCT_RESP__CUSTOMER_COMPLAINT_SATISFACTION', '소비자 불만·만족도', 'Customer complaints and satisfaction', 1, 42, 1),
    ('S_PRODUCT_RESP', '제품책임·고객', 'S_PRODUCT_RESP__PRODUCT_INFORMATION_CHEMICAL_SAFETY', '소비자 정보·화학물질 안전', 'Product information and chemical safety information', 1, 43, 1),
    ('S_PRODUCT_RESP', '제품책임·고객', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', '소비자 건강·제품안전', 'Product safety and quality', 1, 44, 1),
    ('S_PRODUCT_RESP', '제품책임·고객', 'S_PRODUCT_RESP__RECALL_FIELD_ACTION', '리콜·필드액션', 'Recall and field action', 1, 45, 1),
    ('S_PRIVACY', '개인정보·정보보호', 'S_PRIVACY__DATA_BREACH_SECURITY_INCIDENTS', '개인정보 침해·정보보안 사고', 'Data breaches and security incidents', 1, 46, 1),
    ('S_PRIVACY', '개인정보·정보보호', 'S_PRIVACY__PRIVACY_COMPLAINTS_REGULATORY', '개인정보 불만·제재', 'Privacy complaints and regulatory actions', 1, 47, 1),
    ('S_PRIVACY', '개인정보·정보보호', 'S_PRIVACY__PRIVACY_GOVERNANCE', '개인정보보호 체계', 'Privacy governance', 1, 48, 1),
    ('G_GOVERNANCE', '거버넌스·공시', 'G_GOVERNANCE__BOARD_ESG_GOVERNANCE', '이사회·ESG 거버넌스', 'Board and ESG governance', 1, 49, 1),
    ('G_GOVERNANCE', '거버넌스·공시', 'G_GOVERNANCE__BUSINESS_MODEL_VALUE_CHAIN', '사업모델·가치사슬', 'Business model and value chain', 1, 50, 1),
    ('G_GOVERNANCE', '거버넌스·공시', 'G_GOVERNANCE__CORPORATE_PROFILE_REPORTING_BOUNDARY', '기업 프로필·보고경계', 'Corporate profile and reporting boundary', 1, 51, 1),
    ('G_GOVERNANCE', '거버넌스·공시', 'G_GOVERNANCE__ECONOMIC_VALUE', '경제가치 창출·배분', 'Economic value generated and distributed', 1, 52, 1),
    ('G_GOVERNANCE', '거버넌스·공시', 'G_GOVERNANCE__MATERIALITY_STAKEHOLDER', '중대성평가·이해관계자', 'Materiality and stakeholder engagement', 1, 53, 1),
    ('G_RISK', '리스크관리', 'G_RISK__ESG_RISK_MANAGEMENT', 'ESG 리스크 관리', 'ESG risk and opportunity management', 1, 54, 1),
    ('G_ETHICS', '윤리·반부패', 'G_ETHICS__ETHICS_ANTI_CORRUPTION', '윤리경영·반부패', 'Ethics and anti-corruption', 1, 55, 1),
    ('G_ETHICS', '윤리·반부패', 'G_ETHICS__ETHICS_TRAINING', '윤리·부패방지 교육', 'Ethics and anti-corruption training', 1, 56, 1),
    ('G_ETHICS', '윤리·반부패', 'G_ETHICS__WHISTLEBLOWING_RETALIATION', '내부제보·보복금지', 'Whistleblowing and non-retaliation', 1, 57, 1),
    ('G_BUSINESS_CONDUCT', '사업행위·준법', 'G_BUSINESS_CONDUCT__FAIR_COMPETITION', '공정거래·반경쟁', 'Fair competition and anti-competitive conduct', 1, 58, 1),
    ('G_BUSINESS_CONDUCT', '사업행위·준법', 'G_BUSINESS_CONDUCT__LEGAL_COMPLIANCE_VIOLATIONS', '법규준수·위반', 'Legal compliance and violations', 1, 59, 1),
    ('G_BUSINESS_CONDUCT', '사업행위·준법', 'G_BUSINESS_CONDUCT__TAX_PUBLIC_POLICY', '세무·공공정책', 'Tax and public policy', 1, 60, 1),
    ('G_DATA_GOVERNANCE', 'ESG 데이터 거버넌스', 'G_DATA_GOVERNANCE__DISCLOSURE_ASSURANCE', '보고서 승인·검증', 'Report approval and assurance', 1, 61, 1),
    ('G_DATA_GOVERNANCE', 'ESG 데이터 거버넌스', 'G_DATA_GOVERNANCE__ESG_DATA_CONTROL', 'ESG 데이터 내부통제', 'ESG data governance and internal control', 1, 62, 1)
ON DUPLICATE KEY UPDATE issue_group_code=VALUES(issue_group_code), issue_group_name_kr=VALUES(issue_group_name_kr), sub_issue_name_kr=VALUES(sub_issue_name_kr), sub_issue_name_en=VALUES(sub_issue_name_en), materiality_issue_pool_yn=VALUES(materiality_issue_pool_yn), sort_order=VALUES(sort_order), active_yn=VALUES(active_yn);


INSERT INTO ESG_METRIC_MASTER (topic_code, materiality_topic, sub_issue_code, owner_metric_id, metric_id, metric_name_kr, metric_description, mandatory_context_yn, active_yn) VALUES
    ('G0', '경영일반', NULL, 'G0-01', 'G0-01', '회사 개요', '기업의 사업 모델과 주요 역할', 1, 1),
    ('G0', '경영일반', NULL, 'G0-02', 'G0-02', '재무 개요', '각 회사의 별도 기준 매출액', 1, 1),
    ('G0', '경영일반', NULL, 'G0-03', 'G0-03', '사업장 현황', '각 회사의 별도 기준 전체 사업장 수', 1, 1),
    ('G0', '경영일반', NULL, 'G0-04', 'G0-04', '가치사슬', '원재료 조달 및 협력사 활동 설명', 1, 1),
    ('G0', '경영일반', NULL, 'G0-05', 'G0-05', '보고 기준 및 보고 범위', '보고 대상 기간', 1, 1),
    ('G0', '경영일반', NULL, 'G0-06', 'G0-06', '연결 범위', '연결 보고에 포함되는 자회사 목록 및 기준', 1, 1),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', '온실가스 감축 목표 설명', 0, 1),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', '해당 reporting_year의 Scope 1 원천 배출량', 0, 1),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', '총 전력 사용량', 0, 1),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-01', 'S6-01', '공급망 리스크 관리', '공급망 리스크 설명', 0, 1),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-02', 'S6-02', '공급망 실사 체계', '공급망 실사 체계 설명', 0, 1),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', '감사 대상 공급업체 수', 0, 1),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', '공급망 CAP 전체 건수', 0, 1),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', 0, 1),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', '역량개발 중요성', 0, 1),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', '총 교육시간', 0, 1),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', '제품 환경 영향 설명', 0, 1),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', '제품안전 중요성', 0, 1)
ON DUPLICATE KEY UPDATE topic_code=VALUES(topic_code), materiality_topic=VALUES(materiality_topic), sub_issue_code=VALUES(sub_issue_code), owner_metric_id=VALUES(owner_metric_id), metric_name_kr=VALUES(metric_name_kr), metric_description=VALUES(metric_description), mandatory_context_yn=VALUES(mandatory_context_yn), active_yn=VALUES(active_yn);


INSERT INTO ESG_ATOMIC_METRIC_MASTER (topic_code, materiality_topic, sub_issue_code, owner_metric_id, metric_id, metric_name_kr, atomic_metric_id, atomic_name_kr, atomic_name_en, description, data_value_type, atomic_data_role, token_role, onboarding_input_yn, q_token_yn, ql_token_yn, ev_token_yn, event_token_yn, applicable_company_scope, group_link_type_code, rollup_required_yn, rollup_role, rollup_formula, source_atomic_metric_ids, calculation_formula, calculation_rule_code, reference_source_atomic_metric_id, unit, evidence_required_yn, target_db_table, narrative_template_owner_yn, qa_rule) VALUES
    ('G0', '경영일반', NULL, 'G0-01', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', 'QL0001', '기업의 사업 모델과 주요 역할', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-01', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', 'QL0002', '보고서 전반에서 참조되는 주요 제품 및 서비스', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-02', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', 'Q0001', '각 회사의 별도 기준 매출액', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'KRW', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-02', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', 'Q0002', '각 회사의 별도 기준 영업이익', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'KRW', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-02', 'G0-02', '재무 개요', 'G0-02__G0001', '연결 매출액', 'G0001', '연결 매출액', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', 'SUM(G0-02__Q0001 across A/B/C/D)', 'G0-02__Q0001', 'SUM(entity revenue)', 'CR_G0_02_G0001', NULL, 'KRW', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-02', 'G0-02', '재무 개요', 'G0-02__G0002', '연결 영업이익', 'G0002', '연결 영업이익', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', 'SUM(G0-02__Q0002 across A/B/C/D)', 'G0-02__Q0002', 'SUM(entity operating profit)', 'CR_G0_02_G0002', NULL, 'KRW', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-03', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', 'Q0001', '각 회사의 별도 기준 전체 사업장 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-03', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', 'Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-03', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', 'Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-03', 'G0-03', '사업장 현황', 'G0-03__G0001', '연결 전체 사업장 수', 'G0001', '연결 전체 사업장 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'G0-03__Q0001', 'SUM(entity total site count)', 'CR_G0_03_G0001', NULL, '개', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('G0', '경영일반', NULL, 'G0-04', 'G0-04', '가치사슬', 'G0-04__QL0001', 'Upstream 가치사슬 설명', 'QL0001', '원재료 조달 및 협력사 활동 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-04', 'G0-04', '가치사슬', 'G0-04__QL0002', 'Own operation 가치사슬 설명', 'QL0002', '자체 제조·운영 범위 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-04', 'G0-04', '가치사슬', 'G0-04__QL0003', 'Downstream 가치사슬 설명', 'QL0003', '제품 사용·고객·최종 사용자 단계 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-05', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', 'QL0001', '보고 대상 기간', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-05', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0002', '자회사 공시 범위', 'QL0002', '지주사가 연결 공시 범위에 포함하는 자회사와 법인 범위', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-05', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', 'QL0003', '각 회사 본인 기준 사업장, 공장, 연구소, 법인 범위', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-05', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0004', '보고경계 산정 기준', 'QL0004', '자회사 데이터 반영 및 연결 범위 산정 기준', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('G0', '경영일반', NULL, 'G0-06', 'G0-06', '연결 범위', 'G0-06__QL0001', '연결 자회사 범위', 'QL0001', '연결 보고에 포함되는 자회사 목록 및 기준', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0001', '온실가스 감축 목표 설명', 'QL0001', '온실가스 감축 목표 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 1, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', 'QL0002', '감축목표 기준연도', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', 'Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', 'Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0003', '목표연도', 'QL0003', '목표연도', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0003', '감축 목표율', 'Q0003', '감축 목표율', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, '%', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0004', '전환계획 설명', 'QL0004', '전환계획 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0005', '경영진 KPI 연계 설명', 'QL0005', '경영진 KPI 연계 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0001', '기후전략 문서명', 'EV0001', '기후전략 문서명', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, 'CR_E1_05_EV0001', NULL, NULL, 1, 'esg_source_document', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0002', '기후전략 근거 요약', 'EV0002', '기후전략 근거 요약', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, 'CR_E1_05_EV0002', NULL, NULL, 1, 'esg_evidence_chunk', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__G0001', '기준연도 연결 Scope 1 배출량', 'G0001', '기준연도 연결 Scope 1 배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-05__Q0001', 'SUM(entity baseline Scope 1)', 'CR_E1_05_G0001', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__G0002', '기준연도 연결 Scope 2 배출량', 'G0002', '기준연도 연결 Scope 2 배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-05__Q0002', 'SUM(entity baseline Scope 2)', 'CR_E1_05_G0002', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05', '온실가스 감축 목표', 'E1-05__G0003', '기준연도 연결 Scope 1·2 총배출량', 'G0003', '기준연도 연결 Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-05__G0001;E1-05__G0002', 'E1-05__G0001 + E1-05__G0002', 'CR_E1_05_G0003', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', 'Q0001', '해당 reporting_year의 Scope 1 원천 배출량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', 'Q0002', '해당 reporting_year의 Scope 2 원천 배출량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', 'D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'CR_E1_06_D0001', NULL, 'tCO2eq', 0, 'esg_calculation_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', 'D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'CR_E1_06_D0002', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', 'D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'CR_E1_06_D0003', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__G0001', '연결 Scope 1 배출량', 'G0001', '연결 Scope 1 배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-06__Q0001', 'SUM(entity Scope 1 across A/B/C/D)', 'CR_E1_06_G0001', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__G0002', '연결 Scope 2 배출량', 'G0002', '연결 Scope 2 배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-06__Q0002', 'SUM(entity Scope 2 across A/B/C/D)', 'CR_E1_06_G0002', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__G0003', '연결 Scope 1·2 총배출량', 'G0003', '연결 Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-06__G0001;E1-06__G0002', 'G0001 + G0002', 'CR_E1_06_G0003', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__G0004', '연결 전년 대비 온실가스 감축량', 'G0004', '연결 전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'prior_year E1-06__G0003;current_year E1-06__G0003', 'prior year consolidated total - current year consolidated total', 'CR_E1_06_G0004', NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06', '온실가스 감축 실적', 'E1-06__G0005', '연결 전년 대비 온실가스 감축률', 'G0005', '연결 전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-06__G0004;prior_year E1-06__G0003', 'G0004 / prior year G0003 * 100', 'CR_E1_06_G0005', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', 'Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'MWh', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', 'Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'MWh', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', 'D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'CR_E1_07_D0001', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__G0001', '연결 총 전력 사용량', 'G0001', '연결 총 전력 사용량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-07__Q0001', 'SUM(entity total electricity)', 'CR_E1_07_G0001', NULL, 'MWh', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__G0002', '연결 재생에너지 사용량', 'G0002', '연결 재생에너지 사용량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-07__Q0002', 'SUM(entity renewable electricity)', 'CR_E1_07_G0002', NULL, 'MWh', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T01', '기후변화 대응', 'E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07', '재생에너지 전환 실적', 'E1-07__G0003', '연결 재생에너지 전환율', 'G0003', '연결 재생에너지 전환율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'E1-07__G0002;E1-07__G0001', 'G0002 / G0001 * 100', 'CR_E1_07_G0003', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-01', 'S6-01', '공급망 리스크 관리', 'S6-01__QL0001', '공급망 리스크 설명', 'QL0001', '공급망 리스크 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 1, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-02', 'S6-02', '공급망 실사 체계', 'S6-02__QL0001', '공급망 실사 체계 설명', 'QL0001', '공급망 실사 체계 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', 'Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개사', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', 'Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개사', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', 'D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'CR_S6_04_D0001', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', 'Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '개사', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', 'Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', 'Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', 'D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'CR_S6_05_D0001', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__QL0001', '진단 결과 구매정책 반영 설명', 'QL0001', '진단 결과 구매정책 반영 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-02', 'S6-02', '공급망 실사 체계', 'S6-02__EV0001', '공급망 실사 문서명', 'EV0001', '공급망 실사 문서명', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, 'CR_S6_02_EV0001', NULL, NULL, 1, 'esg_source_document', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__EV0001', '공급망 CAP 근거 요약', 'EV0001', '공급망 CAP 근거 요약', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, 'CR_S6_05_EV0001', NULL, NULL, 1, 'esg_evidence_chunk', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__G0001', '연결 감사 대상 공급업체 수', 'G0001', '연결 감사 대상 공급업체 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-04__Q0001', 'SUM', 'CR_S6_04_G0001', NULL, '개사', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__G0002', '연결 감사 완료 공급업체 수', 'G0002', '연결 감사 완료 공급업체 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-04__Q0002', 'SUM', 'CR_S6_04_G0002', NULL, '개사', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__G0003', '연결 공급업체 감사 수행률', 'G0003', '연결 공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-04__D0001', 'G0002 / G0001 * 100', 'CR_S6_04_G0003', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04', '공급업체 감사 수행', 'S6-04__G0004', '연결 고위험 공급업체 수', 'G0004', '연결 고위험 공급업체 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-04__Q0003', 'SUM', 'CR_S6_04_G0004', NULL, '개사', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__G0001', '연결 공급망 CAP 전체 건수', 'G0001', '연결 공급망 CAP 전체 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-05__Q0001', 'SUM', 'CR_S6_05_G0001', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__G0002', '연결 공급망 CAP 완료 건수', 'G0002', '연결 공급망 CAP 완료 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-05__Q0002', 'SUM', 'CR_S6_05_G0002', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T02', '공급망 지속가능성 관리', 'S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05', '공급업체 CAP 관리', 'S6-05__G0003', '연결 공급망 CAP 완료율', 'G0003', '연결 공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S6-05__D0001', 'G0002 / G0001 * 100', 'CR_S6_05_G0003', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', 'Q0001', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', 'Q0002', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', 'Q0003', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', 'Q0004', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', 'Q0005', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', 'Q0006', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', 'Q0007', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', 'Q0008', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', 'Q0009', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', 'Q0010', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', 'Q0011', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', 'Q0012', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', 'Q0013', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', 'Q0014', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', 'Q0015', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', 'Q0016', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', 'Q0017', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', 'Q0018', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', 'Q0019', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', 'Q0020', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', 'Q0021', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', 'Q0022', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', 'Q0023', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', 'Q0024', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', 'Q0025', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', 'Q0026', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', 'Q0027', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', 'Q0028', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', 'Q0029', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', 'Q0030', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', 'Q0031', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', 'Q0032', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', 'Q0033', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', 'Q0034', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required')
ON DUPLICATE KEY UPDATE topic_code=VALUES(topic_code), materiality_topic=VALUES(materiality_topic), sub_issue_code=VALUES(sub_issue_code), owner_metric_id=VALUES(owner_metric_id), metric_id=VALUES(metric_id), metric_name_kr=VALUES(metric_name_kr), atomic_name_kr=VALUES(atomic_name_kr), atomic_name_en=VALUES(atomic_name_en), description=VALUES(description), data_value_type=VALUES(data_value_type), atomic_data_role=VALUES(atomic_data_role), token_role=VALUES(token_role), onboarding_input_yn=VALUES(onboarding_input_yn), q_token_yn=VALUES(q_token_yn), ql_token_yn=VALUES(ql_token_yn), ev_token_yn=VALUES(ev_token_yn), event_token_yn=VALUES(event_token_yn), applicable_company_scope=VALUES(applicable_company_scope), group_link_type_code=VALUES(group_link_type_code), rollup_required_yn=VALUES(rollup_required_yn), rollup_role=VALUES(rollup_role), rollup_formula=VALUES(rollup_formula), source_atomic_metric_ids=VALUES(source_atomic_metric_ids), calculation_formula=VALUES(calculation_formula), calculation_rule_code=VALUES(calculation_rule_code), reference_source_atomic_metric_id=VALUES(reference_source_atomic_metric_id), unit=VALUES(unit), evidence_required_yn=VALUES(evidence_required_yn), target_db_table=VALUES(target_db_table), narrative_template_owner_yn=VALUES(narrative_template_owner_yn), qa_rule=VALUES(qa_rule);


INSERT INTO ESG_ATOMIC_METRIC_MASTER (topic_code, materiality_topic, sub_issue_code, owner_metric_id, metric_id, metric_name_kr, atomic_metric_id, atomic_name_kr, atomic_name_en, description, data_value_type, atomic_data_role, token_role, onboarding_input_yn, q_token_yn, ql_token_yn, ev_token_yn, event_token_yn, applicable_company_scope, group_link_type_code, rollup_required_yn, rollup_role, rollup_formula, source_atomic_metric_ids, calculation_formula, calculation_rule_code, reference_source_atomic_metric_id, unit, evidence_required_yn, target_db_table, narrative_template_owner_yn, qa_rule) VALUES
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', 'Q0035', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', 'Q0036', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', 'Q0037', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', 'Q0038', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', 'Q0039', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', 'Q0040', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', 'Q0041', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', 'Q0042', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', 'Q0043', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', 'Q0044', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', 'Q0045', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', 'Q0046', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', 'Q0047', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', 'Q0048', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', 'Q0049', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', 'Q0050', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', 'Q0051', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', 'Q0052', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', 'Q0053', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', 'Q0054', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', 'Q0055', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', 'Q0056', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', 'Q0057', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', 'Q0058', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', 'Q0059', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', 'Q0060', '성별·연령·고용형태·지역 조합을 atomic_metric_id로 펼친 임직원 수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', 'D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'CR_S1_02_D0001', NULL, '명', 0, 'esg_calculation_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', 'D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'CR_S1_02_D0002', NULL, '%', 0, 'esg_calculation_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', 'D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'CR_S1_02_D0003', NULL, '%', 0, 'esg_calculation_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', 'D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source_derived', NULL, 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'CR_S1_02_D0004', NULL, '%', 0, 'esg_calculation_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__G0001', '연결 전체 임직원 수', 'G0001', '연결 전체 임직원 수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S1-02__D0001', 'SUM(entity total employees)', 'CR_S1_02_G0001', NULL, '명', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__G0002', '연결 여성 임직원 비율', 'G0002', '연결 여성 임직원 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S1-02 female Q atoms', 'SUM(female employees) / SUM(total employees) * 100', 'CR_S1_02_G0002', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__G0003', '연결 정규직 비율', 'G0003', '연결 정규직 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S1-02 regular Q atoms', 'SUM(regular employees) / SUM(total employees) * 100', 'CR_S1_02_G0003', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02', '임직원 구성', 'S1-02__G0004', '연결 해외 임직원 비율', 'G0004', '연결 해외 임직원 비율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S1-02 EU/US Q atoms', 'SUM(EU/US employees) / SUM(total employees) * 100', 'CR_S1_02_G0004', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0001', '역량개발 중요성', 'QL0001', '역량개발 중요성', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 1, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0002', '교육 전략', 'QL0002', '교육 전략', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0003', 'SW아카데미 설명', 'QL0003', 'SW아카데미 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0004', '글로벌 전문가 과정 설명', 'QL0004', '글로벌 전문가 과정 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', 'Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '시간', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', 'R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_S3_02_R0001', 'S1-02__D0001', '명', 0, 'esg_reference_value', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', 'D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'CR_S3_02_D0001', NULL, '시간/명', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', 'Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', 'Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '명', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', 'D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'CR_S3_02_D0002', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0001', '교육관리 지침 문서명', 'EV0001', '교육관리 지침 문서명', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_S3_01_EV0001', NULL, NULL, 1, 'esg_source_document', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0002', '교육관리 지침 근거 요약', 'EV0002', '교육관리 지침 근거 요약', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_S3_01_EV0002', NULL, NULL, 1, 'esg_evidence_chunk', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__G0001', '연결 총 교육시간', 'G0001', '연결 총 교육시간', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S3-02__Q0001', 'SUM(entity total training hours)', 'CR_S3_02_G0001', NULL, '시간', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__G0002', '연결 1인당 교육시간', 'G0002', '연결 1인당 교육시간', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S3-02__G0001;S1-02__G0001', 'SUM(training hours) / connected employee count', 'CR_S3_02_G0002', NULL, '시간/명', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T03', '인적자원 관리', 'S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02', '교육성과', 'S3-02__G0003', '연결 핵심직무 교육 달성률', 'G0003', '연결 핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'S3-02__Q0003;S3-02__Q0002', 'SUM(completed) / SUM(target) * 100', 'CR_S3_02_G0003', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0001', '제품 환경 영향 설명', 'QL0001', '제품 환경 영향 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 1, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0002', '저탄소 제품 포트폴리오 설명', 'QL0002', '저탄소 제품 포트폴리오 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', 'Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'KRW', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', 'R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_AP_E_06_R0001', 'G0-02__Q0001', 'KRW', 0, 'esg_reference_value', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', 'D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'CR_AP_E_06_D0001', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', 'Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'tCO2eq', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', 'Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, 'KRW', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0001', '친환경 제품·LCA 문서명', 'EV0001', '친환경 제품·LCA 문서명', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_AP_E_06_EV0001', NULL, NULL, 1, 'esg_source_document', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0002', '친환경 제품·LCA 근거 요약', 'EV0002', '친환경 제품·LCA 근거 요약', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_AP_E_06_EV0002', NULL, NULL, 1, 'esg_evidence_chunk', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__G0001', '연결 친환경 제품 매출액', 'G0001', '연결 친환경 제품 매출액', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-E-06__Q0001', 'SUM(entity low carbon product revenue)', 'CR_AP_E_06_G0001', NULL, 'KRW', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__G0002', '연결 전체 매출액 참조', 'G0002', '연결 전체 매출액 참조', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'G0-02__G0001', 'G0-02__G0001', 'CR_AP_E_06_G0002', NULL, 'KRW', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__G0003', '연결 친환경 제품 매출 비중', 'G0003', '연결 친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-E-06__G0001;AP-E-06__G0002', 'G0001 / G0002 * 100', 'CR_AP_E_06_G0003', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__G0004', '연결 회피 배출량', 'G0004', '연결 회피 배출량', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-E-06__Q0002', 'SUM(entity avoided emissions)', 'CR_AP_E_06_G0004', NULL, 'tCO2eq', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T04', '자원 사용 및 순환 경제', 'E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__G0005', '연결 사회적 비용 절감 효과', 'G0005', '연결 사회적 비용 절감 효과', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-E-06__Q0003', 'SUM(entity social cost savings)', 'CR_AP_E_06_G0005', NULL, 'KRW', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0001', '제품안전 중요성', 'QL0001', '제품안전 중요성', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 1, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0002', '제품안전 관리체계', 'QL0002', '제품안전 관리체계', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0003', '품질 인증 설명', 'QL0003', '품질 인증 설명', '정성', 'INPUT', 'QL', 1, 0, 1, 0, 0, 'A_GROUP_ONLY', 'GROUP_POLICY', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', 'Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', 'Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', 'EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', 1, 0, 1, 0, 1, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'esg_event_cap_register', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', 'Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', 'Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 1, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 1, 'source', 'SUM', NULL, NULL, NULL, NULL, '건', 0, 'esg_onboarding_input_value', 0, 'INPUT row must have value in 02_DUMMY_INPUT_FACT_3YR for applicable company/year; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', 'D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'ALL_COMPANIES', 'ENTITY_SOURCE', 0, NULL, NULL, 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'CR_AP_S_01_D0001', NULL, '%', 0, 'esg_onboarding_input_value', 0, 'DERIVED row must have calculation_formula and computed value'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0001', '제품안전·품질·리콜 절차서 문서명', 'EV0001', '제품안전·품질·리콜 절차서 문서명', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_AP_S_01_EV0001', NULL, NULL, 1, 'esg_source_document', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0002', '제품안전·품질·리콜 근거 요약', 'EV0002', '제품안전·품질·리콜 근거 요약', '정성', 'REFERENCE', 'EV', 0, 0, 0, 1, 0, 'A_GROUP_ONLY', 'ENTITY_SOURCE', 0, NULL, NULL, NULL, NULL, 'CR_AP_S_01_EV0002', NULL, NULL, 1, 'esg_evidence_chunk', 0, 'REFERENCE row must link to source document or source atomic'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__G0001', '연결 필드액션 건수', 'G0001', '연결 필드액션 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-S-01__Q0001', 'SUM(entity field action count)', 'CR_AP_S_01_G0001', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__G0002', '연결 리콜 건수', 'G0002', '연결 리콜 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-S-01__Q0002', 'SUM(entity recall count)', 'CR_AP_S_01_G0002', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__G0003', '연결 제품안전 CAP 전체 건수', 'G0003', '연결 제품안전 CAP 전체 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-S-01__Q0003', 'SUM(entity CAP total)', 'CR_AP_S_01_G0003', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__G0004', '연결 제품안전 CAP 완료 건수', 'G0004', '연결 제품안전 CAP 완료 건수', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-S-01__Q0004', 'SUM(entity CAP completed)', 'CR_AP_S_01_G0004', NULL, '건', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required'),
    ('T05', '제품 품질 및 안전 확보', 'S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__G0005', '연결 제품안전 CAP 완료율', 'G0005', '연결 제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 0, 1, 0, 0, 0, 'A_GROUP_CONSOLIDATED', 'GROUP_CONSOLIDATED', 1, 'consolidated_result', NULL, 'AP-S-01__G0004;AP-S-01__G0003', 'G0004 / G0003 * 100', 'CR_AP_S_01_G0005', NULL, '%', 0, 'esg_group_rollup_result', 0, 'DERIVED row must have calculation_formula and computed value; rollup trace required')
ON DUPLICATE KEY UPDATE topic_code=VALUES(topic_code), materiality_topic=VALUES(materiality_topic), sub_issue_code=VALUES(sub_issue_code), owner_metric_id=VALUES(owner_metric_id), metric_id=VALUES(metric_id), metric_name_kr=VALUES(metric_name_kr), atomic_name_kr=VALUES(atomic_name_kr), atomic_name_en=VALUES(atomic_name_en), description=VALUES(description), data_value_type=VALUES(data_value_type), atomic_data_role=VALUES(atomic_data_role), token_role=VALUES(token_role), onboarding_input_yn=VALUES(onboarding_input_yn), q_token_yn=VALUES(q_token_yn), ql_token_yn=VALUES(ql_token_yn), ev_token_yn=VALUES(ev_token_yn), event_token_yn=VALUES(event_token_yn), applicable_company_scope=VALUES(applicable_company_scope), group_link_type_code=VALUES(group_link_type_code), rollup_required_yn=VALUES(rollup_required_yn), rollup_role=VALUES(rollup_role), rollup_formula=VALUES(rollup_formula), source_atomic_metric_ids=VALUES(source_atomic_metric_ids), calculation_formula=VALUES(calculation_formula), calculation_rule_code=VALUES(calculation_rule_code), reference_source_atomic_metric_id=VALUES(reference_source_atomic_metric_id), unit=VALUES(unit), evidence_required_yn=VALUES(evidence_required_yn), target_db_table=VALUES(target_db_table), narrative_template_owner_yn=VALUES(narrative_template_owner_yn), qa_rule=VALUES(qa_rule);


INSERT INTO ESG_SUB_ISSUE_ATOMIC_MAP (sub_issue_code, metric_id, atomic_metric_id, map_scope, required_yn, sort_order) VALUES
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__QL0001', 'MVP_SELECTED', 1, 1),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__QL0002', 'MVP_SELECTED', 1, 2),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__Q0001', 'MVP_SELECTED', 1, 3),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__Q0002', 'MVP_SELECTED', 1, 4),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__QL0003', 'MVP_SELECTED', 1, 5),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__Q0003', 'MVP_SELECTED', 1, 6),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__QL0004', 'MVP_SELECTED', 1, 7),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__QL0005', 'MVP_SELECTED', 1, 8),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__EV0001', 'MVP_SELECTED', 1, 9),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__EV0002', 'MVP_SELECTED', 1, 10),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__G0001', 'MVP_SELECTED', 1, 11),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__G0002', 'MVP_SELECTED', 1, 12),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-05', 'E1-05__G0003', 'MVP_SELECTED', 1, 13),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__Q0001', 'MVP_SELECTED', 1, 14),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__Q0002', 'MVP_SELECTED', 1, 15),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__D0001', 'MVP_SELECTED', 1, 16),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__D0002', 'MVP_SELECTED', 1, 17),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__D0003', 'MVP_SELECTED', 1, 18),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__G0001', 'MVP_SELECTED', 1, 19),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__G0002', 'MVP_SELECTED', 1, 20),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__G0003', 'MVP_SELECTED', 1, 21),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__G0004', 'MVP_SELECTED', 1, 22),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-06', 'E1-06__G0005', 'MVP_SELECTED', 1, 23),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__Q0001', 'MVP_SELECTED', 1, 24),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__Q0002', 'MVP_SELECTED', 1, 25),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__D0001', 'MVP_SELECTED', 1, 26),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__G0001', 'MVP_SELECTED', 1, 27),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__G0002', 'MVP_SELECTED', 1, 28),
    ('E_CLIMATE__CLIMATE_TARGETS_TRANSITION', 'E1-07', 'E1-07__G0003', 'MVP_SELECTED', 1, 29),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-01', 'S6-01__QL0001', 'MVP_SELECTED', 1, 30),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-02', 'S6-02__QL0001', 'MVP_SELECTED', 1, 31),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__Q0001', 'MVP_SELECTED', 1, 32),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__Q0002', 'MVP_SELECTED', 1, 33),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__D0001', 'MVP_SELECTED', 1, 34),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__Q0003', 'MVP_SELECTED', 1, 35),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__Q0001', 'MVP_SELECTED', 1, 36),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__Q0002', 'MVP_SELECTED', 1, 37),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__D0001', 'MVP_SELECTED', 1, 38),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__QL0001', 'MVP_SELECTED', 1, 39),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-02', 'S6-02__EV0001', 'MVP_SELECTED', 1, 40),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__EV0001', 'MVP_SELECTED', 1, 41),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__G0001', 'MVP_SELECTED', 1, 42),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__G0002', 'MVP_SELECTED', 1, 43),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__G0003', 'MVP_SELECTED', 1, 44),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-04', 'S6-04__G0004', 'MVP_SELECTED', 1, 45),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__G0001', 'MVP_SELECTED', 1, 46),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__G0002', 'MVP_SELECTED', 1, 47),
    ('S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP', 'S6-05', 'S6-05__G0003', 'MVP_SELECTED', 1, 48),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0001', 'MVP_SELECTED', 1, 49),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0002', 'MVP_SELECTED', 1, 50),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0003', 'MVP_SELECTED', 1, 51),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0004', 'MVP_SELECTED', 1, 52),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0005', 'MVP_SELECTED', 1, 53),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0006', 'MVP_SELECTED', 1, 54),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0007', 'MVP_SELECTED', 1, 55),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0008', 'MVP_SELECTED', 1, 56),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0009', 'MVP_SELECTED', 1, 57),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0010', 'MVP_SELECTED', 1, 58),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0011', 'MVP_SELECTED', 1, 59),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0012', 'MVP_SELECTED', 1, 60),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0013', 'MVP_SELECTED', 1, 61),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0014', 'MVP_SELECTED', 1, 62),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0015', 'MVP_SELECTED', 1, 63),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0016', 'MVP_SELECTED', 1, 64),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0017', 'MVP_SELECTED', 1, 65),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0018', 'MVP_SELECTED', 1, 66),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0019', 'MVP_SELECTED', 1, 67),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0020', 'MVP_SELECTED', 1, 68),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0021', 'MVP_SELECTED', 1, 69),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0022', 'MVP_SELECTED', 1, 70),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0023', 'MVP_SELECTED', 1, 71),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0024', 'MVP_SELECTED', 1, 72),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0025', 'MVP_SELECTED', 1, 73),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0026', 'MVP_SELECTED', 1, 74),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0027', 'MVP_SELECTED', 1, 75),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0028', 'MVP_SELECTED', 1, 76),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0029', 'MVP_SELECTED', 1, 77),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0030', 'MVP_SELECTED', 1, 78),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0031', 'MVP_SELECTED', 1, 79),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0032', 'MVP_SELECTED', 1, 80),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0033', 'MVP_SELECTED', 1, 81),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0034', 'MVP_SELECTED', 1, 82),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0035', 'MVP_SELECTED', 1, 83),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0036', 'MVP_SELECTED', 1, 84),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0037', 'MVP_SELECTED', 1, 85),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0038', 'MVP_SELECTED', 1, 86),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0039', 'MVP_SELECTED', 1, 87),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0040', 'MVP_SELECTED', 1, 88),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0041', 'MVP_SELECTED', 1, 89),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0042', 'MVP_SELECTED', 1, 90),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0043', 'MVP_SELECTED', 1, 91),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0044', 'MVP_SELECTED', 1, 92),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0045', 'MVP_SELECTED', 1, 93),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0046', 'MVP_SELECTED', 1, 94),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0047', 'MVP_SELECTED', 1, 95),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0048', 'MVP_SELECTED', 1, 96),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0049', 'MVP_SELECTED', 1, 97),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0050', 'MVP_SELECTED', 1, 98),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0051', 'MVP_SELECTED', 1, 99),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0052', 'MVP_SELECTED', 1, 100)
ON DUPLICATE KEY UPDATE map_scope=VALUES(map_scope), required_yn=VALUES(required_yn), sort_order=VALUES(sort_order);


INSERT INTO ESG_SUB_ISSUE_ATOMIC_MAP (sub_issue_code, metric_id, atomic_metric_id, map_scope, required_yn, sort_order) VALUES
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0053', 'MVP_SELECTED', 1, 101),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0054', 'MVP_SELECTED', 1, 102),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0055', 'MVP_SELECTED', 1, 103),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0056', 'MVP_SELECTED', 1, 104),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0057', 'MVP_SELECTED', 1, 105),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0058', 'MVP_SELECTED', 1, 106),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0059', 'MVP_SELECTED', 1, 107),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__Q0060', 'MVP_SELECTED', 1, 108),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__D0001', 'MVP_SELECTED', 1, 109),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__D0002', 'MVP_SELECTED', 1, 110),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__D0003', 'MVP_SELECTED', 1, 111),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__D0004', 'MVP_SELECTED', 1, 112),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__G0001', 'MVP_SELECTED', 1, 113),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__G0002', 'MVP_SELECTED', 1, 114),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__G0003', 'MVP_SELECTED', 1, 115),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S1-02', 'S1-02__G0004', 'MVP_SELECTED', 1, 116),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__QL0001', 'MVP_SELECTED', 1, 117),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__QL0002', 'MVP_SELECTED', 1, 118),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__QL0003', 'MVP_SELECTED', 1, 119),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__QL0004', 'MVP_SELECTED', 1, 120),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__Q0001', 'MVP_SELECTED', 1, 121),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__R0001', 'MVP_SELECTED', 1, 122),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__D0001', 'MVP_SELECTED', 1, 123),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__Q0002', 'MVP_SELECTED', 1, 124),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__Q0003', 'MVP_SELECTED', 1, 125),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__D0002', 'MVP_SELECTED', 1, 126),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__EV0001', 'MVP_SELECTED', 1, 127),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-01', 'S3-01__EV0002', 'MVP_SELECTED', 1, 128),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__G0001', 'MVP_SELECTED', 1, 129),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__G0002', 'MVP_SELECTED', 1, 130),
    ('S_TALENT__TRAINING_DEVELOPMENT', 'S3-02', 'S3-02__G0003', 'MVP_SELECTED', 1, 131),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__QL0001', 'MVP_SELECTED', 1, 132),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__QL0002', 'MVP_SELECTED', 1, 133),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__Q0001', 'MVP_SELECTED', 1, 134),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__R0001', 'MVP_SELECTED', 1, 135),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__D0001', 'MVP_SELECTED', 1, 136),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__Q0002', 'MVP_SELECTED', 1, 137),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__Q0003', 'MVP_SELECTED', 1, 138),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__EV0001', 'MVP_SELECTED', 1, 139),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__EV0002', 'MVP_SELECTED', 1, 140),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__G0001', 'MVP_SELECTED', 1, 141),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__G0002', 'MVP_SELECTED', 1, 142),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__G0003', 'MVP_SELECTED', 1, 143),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__G0004', 'MVP_SELECTED', 1, 144),
    ('E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE', 'AP-E-06', 'AP-E-06__G0005', 'MVP_SELECTED', 1, 145),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__QL0001', 'MVP_SELECTED', 1, 146),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__QL0002', 'MVP_SELECTED', 1, 147),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__QL0003', 'MVP_SELECTED', 1, 148),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__Q0001', 'MVP_SELECTED', 1, 149),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__Q0002', 'MVP_SELECTED', 1, 150),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__EVT0001', 'MVP_SELECTED', 1, 151),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__Q0003', 'MVP_SELECTED', 1, 152),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__Q0004', 'MVP_SELECTED', 1, 153),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__D0001', 'MVP_SELECTED', 1, 154),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__EV0001', 'MVP_SELECTED', 1, 155),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__EV0002', 'MVP_SELECTED', 1, 156),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__G0001', 'MVP_SELECTED', 1, 157),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__G0002', 'MVP_SELECTED', 1, 158),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__G0003', 'MVP_SELECTED', 1, 159),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__G0004', 'MVP_SELECTED', 1, 160),
    ('S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY', 'AP-S-01', 'AP-S-01__G0005', 'MVP_SELECTED', 1, 161)
ON DUPLICATE KEY UPDATE map_scope=VALUES(map_scope), required_yn=VALUES(required_yn), sort_order=VALUES(sort_order);


-- ---------------------------------------------------------------------
-- 1~3. Company profile / rollup candidate scope / dummy input staging / input values
-- ---------------------------------------------------------------------
-- ---------------------------------------------------------------------
-- 1. Company profile and rollup scope
-- ---------------------------------------------------------------------
INSERT INTO ESG_COMPANY_PROFILE (company_id, company_code, company_scope_type, active_yn) VALUES
    (@company_id_A_GROUP, 'A_GROUP', 'PARENT', 1),
    (@company_id_B_SUB_KR, 'B_SUB_KR', 'SUBSIDIARY', 1),
    (@company_id_C_SUB_EU, 'C_SUB_EU', 'SUBSIDIARY', 1),
    (@company_id_D_SUB_US, 'D_SUB_US', 'SUBSIDIARY', 1)
ON DUPLICATE KEY UPDATE company_id=VALUES(company_id), company_scope_type=VALUES(company_scope_type), active_yn=VALUES(active_yn);

INSERT INTO ESG_COMPANY_ROLLUP_SCOPE (parent_company_id, source_company_id, source_company_code, rollup_include_yn, effective_from_year, effective_to_year, note) VALUES
    (@company_id_A_GROUP, @company_id_A_GROUP, 'A_GROUP', 1, 2022, NULL, 'MVP v5.2 full onboarding seed rollup scope'),
    (@company_id_A_GROUP, @company_id_B_SUB_KR, 'B_SUB_KR', 1, 2022, NULL, 'MVP v5.2 full onboarding seed rollup scope'),
    (@company_id_A_GROUP, @company_id_C_SUB_EU, 'C_SUB_EU', 1, 2022, NULL, 'MVP v5.2 full onboarding seed rollup scope'),
    (@company_id_A_GROUP, @company_id_D_SUB_US, 'D_SUB_US', 1, 2022, NULL, 'MVP v5.2 full onboarding seed rollup scope')
ON DUPLICATE KEY UPDATE rollup_include_yn=VALUES(rollup_include_yn), effective_to_year=VALUES(effective_to_year), note=VALUES(note);

-- ---------------------------------------------------------------------
-- 2. Full onboarding dummy staging: 3 years × A/B/C/D × atomic facts
-- ---------------------------------------------------------------------
-- ---------------------------------------------------------------------
-- 3. Full onboarding dummy staging: 3 years × A/B/C/D × atomic facts
-- ---------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS TMP_ESG_DUMMY_INPUT_FACT;
CREATE TEMPORARY TABLE TMP_ESG_DUMMY_INPUT_FACT (
    fact_row_id VARCHAR(150) NOT NULL,
    reporting_year INT NOT NULL,
    company_code VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NULL,
    company_scope_type VARCHAR(30) NOT NULL,
    materiality_topic VARCHAR(200) NULL,
    sub_issue_label VARCHAR(300) NULL,
    metric_id VARCHAR(50) NOT NULL,
    metric_name_kr VARCHAR(300) NULL,
    atomic_metric_id VARCHAR(80) NOT NULL,
    atomic_name_kr VARCHAR(300) NULL,
    data_value_type VARCHAR(20) NULL,
    atomic_data_role VARCHAR(30) NULL,
    token_role VARCHAR(20) NULL,
    value_numeric DECIMAL(30,6) NULL,
    value_text LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    value_source_type VARCHAR(30) NULL,
    approval_status VARCHAR(30) NULL,
    approved_by_user_code VARCHAR(100) NULL,
    approved_at DATETIME NULL,
    source_atomic_metric_ids TEXT NULL,
    calculation_trace TEXT NULL,
    group_link_type_code VARCHAR(50) NULL,
    rollup_required_yn VARCHAR(10) NULL,
    note TEXT NULL,
    PRIMARY KEY (fact_row_id)
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2022_A_GROUP_G0-01__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 자동차 부품과 전동화 부품 사업을 총괄하는 지주회사로, 국내외 자회사와 함께 모빌리티 부품 사업을 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-01__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-02__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 1200000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-02__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 84000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-03__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-03__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-03__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-04__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0001', 'Upstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Upstream 단계에서는 원재료 조달, 부품 가공, 협력사 생산 활동을 포함하며 공급망 환경·인권 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-04__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0002', 'Own operation 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Own operation 단계에서는 본사, 연구소, 생산거점의 제조·품질·환경안전 활동을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-04__QL0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0003', 'Downstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Downstream 단계에서는 고객사 납품, 제품 사용, 서비스 부품 공급과 관련한 품질·안전·환경성과를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-05__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2022.01.01~2022.12.31', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-05__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0002', '자회사 공시 범위', '정성', 'INPUT', 'QL', NULL, '연결 공시 범위에는 A_GROUP 본인 사업장과 B_SUB_KR, C_SUB_EU, D_SUB_US를 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-05__QL0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '본사, 국내 연구소, 그룹 관리 조직 및 일부 지원 거점을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-05__QL0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0004', '보고경계 산정 기준', '정성', 'INPUT', 'QL', NULL, '보고경계는 연결 재무 기준과 ESG 데이터 관리 범위를 함께 고려하며, 자회사 승인값은 롤업 요청 후 연결 기준으로 반영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_G0-06__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-06', '연결 범위', 'G0-06__QL0001', '연결 자회사 범위', '정성', 'INPUT', 'QL', NULL, '연결 범위는 지주사 A_GROUP과 국내 자회사 B_SUB_KR, EU 자회사 C_SUB_EU, 미국 자회사 D_SUB_US로 구성한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0001', '온실가스 감축 목표 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 2045년 탄소중립과 2040년 재생에너지 100% 전환을 목표로 Scope 1·2 배출 감축과 전환계획을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 10620, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 7410, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__QL0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0003', '목표연도', '정성', 'INPUT', 'QL', NULL, '2045', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0003', '감축 목표율', '정량', 'INPUT', 'Q', 100, NULL, '%', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__QL0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0004', '전환계획 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 조달, 고효율 설비 전환, 생산공정 에너지 효율화, 자회사별 감축 과제 점검을 전환계획의 주요 이행수단으로 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__QL0005', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0005', '경영진 KPI 연계 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 전환율과 온실가스 감축 실적을 경영진 KPI에 연계하여 연 단위로 이행 현황을 점검한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-05__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0001', '기후전략 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-E1-001 A_GROUP 기후전략 및 온실가스 관리 규정', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2022_A_GROUP_E1-05__EV0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0002', '기후전략 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '기후전략 문서는 탄소중립 목표, 기준연도, Scope 1·2 감축관리, 재생에너지 전환 KPI 및 경영진 보고 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2022_A_GROUP_E1-06__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 9000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-06__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 6500, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-06__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 15500, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_E1-06__D0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', NULL, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_E1-06__D0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', NULL, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_E1-07__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 25000, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-07__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 1750, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_E1-07__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 7, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S6-01__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-01', '공급망 리스크 관리', 'S6-01__QL0001', '공급망 리스크 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 주요 협력사의 환경·인권·윤리 리스크가 조달 안정성과 브랜드 신뢰에 미치는 영향을 고려해 공급망 지속가능성 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-02__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__QL0001', '공급망 실사 체계 설명', '정성', 'INPUT', 'QL', NULL, '공급망 실사는 사전평가, 현장진단, 고위험 협력사 식별, CAP 부여 및 구매정책 반영의 순서로 운영된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-04__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 60, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-04__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 43, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-04__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 71.67, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S6-04__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 7, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-05__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 15, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-05__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 10, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-05__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 66.67, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S6-05__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__QL0001', '진단 결과 구매정책 반영 설명', '정성', 'INPUT', 'QL', NULL, '진단 결과는 고위험 협력사 개선계획과 구매정책 검토에 반영되며, CAP 이행 현황은 정기적으로 모니터링한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S6-02__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__EV0001', '공급망 실사 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S6-001 공급망 ESG 실사 및 CAP 운영 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2022_A_GROUP_S6-05__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__EV0001', '공급망 CAP 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '공급망 절차서는 협력사 진단 범위, 감사 기준, CAP 이행관리, 결과의 구매정책 반영 기준을 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2022_A_GROUP_S1-02__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 40, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 114, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0005', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 97, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0006', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0007', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 64, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0008', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0009', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0010', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0011', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 25, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0012', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0013', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 70, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0014', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0015', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 60, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0016', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0017', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 39, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0018', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0019', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0020', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0021', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0022', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0023', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 23, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0024', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0025', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 19, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0026', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0027', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0028', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0029', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0030', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0031', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0032', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0033', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0034', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0035', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0036', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0037', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0038', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0039', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0040', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0041', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0042', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0043', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0044', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0045', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0046', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0047', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0048', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0049', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0050', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0051', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0052', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0053', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0054', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0055', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0056', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0057', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0058', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0059', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__Q0060', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S1-02__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 820, NULL, '명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S1-02__D0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.93, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S1-02__D0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 87.93, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S1-02__D0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 25, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_A_GROUP_S3-01__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0001', '역량개발 중요성', '정성', 'INPUT', 'QL', NULL, '전동화·자율주행·디지털화 전환에 대응하기 위해 미래 모빌리티 기술 인재 확보와 내부 역량 강화가 중요하다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-01__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0002', '교육 전략', '정성', 'INPUT', 'QL', NULL, '직무별 모듈형 교육과 핵심기술 교육을 통해 연구개발, 소프트웨어, 친환경 기술 역량을 강화한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-01__QL0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0003', 'SW아카데미 설명', '정성', 'INPUT', 'QL', NULL, 'SW아카데미는 연구개발 및 소프트웨어 직무 인력을 대상으로 실무 프로젝트 기반 교육을 제공한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-01__QL0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0004', '글로벌 전문가 과정 설명', '정성', 'INPUT', 'QL', NULL, '글로벌 전문가 과정은 해외법인과 글로벌 고객 대응 인력의 사업 수행 역량을 강화하는 프로그램이다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-02__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 27552, NULL, '시간', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-02__R0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 820, NULL, '명', 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_S3-02__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 33.6, NULL, '시간/명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_S3-02__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 344, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-02__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 248, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_S3-02__D0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 72.09, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_S3-01__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0001', '교육관리 지침 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S3-001 교육훈련 및 역량개발 운영 지침', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_S3-01__EV0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0002', '교육관리 지침 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '교육관리 지침은 교육 프로그램 분류, 대상자 관리, 수료 기준, 교육시간 산정 및 성과 모니터링 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-E-06__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0001', '제품 환경 영향 설명', '정성', 'INPUT', 'QL', NULL, '전동화 부품과 경량화·고효율 부품은 제품 사용 단계의 온실가스 감축과 환경영향 저감에 기여한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-E-06__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0002', '저탄소 제품 포트폴리오 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 전동화 부품, 배출저감 기여 부품, 경량화 부품을 중심으로 저탄소 제품 포트폴리오를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-E-06__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 216000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-E-06__R0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 1200000000000, NULL, 'KRW', 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-E-06__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 18, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-E-06__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 45000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-E-06__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 2493000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-E-06__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0001', '친환경 제품·LCA 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APE-001 친환경 제품 및 LCA 관리 기준', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-E-06__EV0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0002', '친환경 제품·LCA 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '친환경 제품 기준은 제품군별 환경성과, 회피 배출량 산정 방법, LCA 검토 절차와 성과관리 지표를 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-S-01__QL0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0001', '제품안전 중요성', '정성', 'INPUT', 'QL', NULL, '제품 품질과 안전은 고객 신뢰, 규제 대응, 필드 리스크 관리에 직접 연결되는 핵심 주제다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__QL0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0002', '제품안전 관리체계', '정성', 'INPUT', 'QL', NULL, '제품안전 관리체계는 설계 검증, 양산 품질관리, 고객사 필드이슈 접수, 원인분석 및 CAP 이행으로 구성된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__QL0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0003', '품질 인증 설명', '정성', 'INPUT', 'QL', NULL, '주요 제품군은 품질 인증과 안전성 평가를 통해 출하 전 검증 절차를 거치며, 고위험 이슈는 별도 심의체계로 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__Q0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__Q0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 0, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__EVT0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2022년 전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__Q0003', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__Q0004', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2022_A_GROUP_AP-S-01__D0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 66.67, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-S-01__EV0001', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0001', '제품안전·품질·리콜 절차서 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APS-001 제품안전·품질·리콜 관리 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_A_GROUP_AP-S-01__EV0002', 2022, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0002', '제품안전·품질·리콜 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '제품안전 절차서는 필드액션, 리콜, 시정조치, 예방조치 및 고객사 보고 기준을 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_G0-01__QL0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'B_SUB_KR은 국내 생산과 연구개발을 담당하는 자동차 부품 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_G0-01__QL0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 모듈, 섀시 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_G0-02__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 8200000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_G0-02__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 451000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_G0-03__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 8, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_G0-03__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 8, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_G0-03__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_G0-05__QL0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2022.01.01~2022.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_G0-05__QL0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '국내 생산공장, 연구개발 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_E1-05__QL0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_E1-05__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 30680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-05__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 20520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-06__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 26000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-06__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 18000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-06__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 44000, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-06__D0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', NULL, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-06__D0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', NULL, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-07__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 92000, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-07__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 5520, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_E1-07__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 6, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-04__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 260, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-04__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 187, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-04__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 71.92, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-04__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 29, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-05__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 64, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-05__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 44, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S6-05__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 68.75, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 253, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 34, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 717, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0004', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 98, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0005', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 611, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0006', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 83, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0007', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 401, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0008', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 55, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0009', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 126, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0010', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0011', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 155, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0012', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0013', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 439, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0014', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 60, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0015', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 375, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0016', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 51, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0017', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 246, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0018', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 33, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0019', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 78, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0020', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0021', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0022', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0023', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 31, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0024', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0025', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0026', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0027', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0028', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0029', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0030', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0031', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0032', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0033', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 19, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0034', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0035', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0036', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0037', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0038', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0039', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0040', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0041', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0042', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0043', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 31, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0044', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0045', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0046', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0047', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0048', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0049', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0050', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0051', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0052', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0053', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 19, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0054', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0055', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0056', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0057', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0058', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0059', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__Q0060', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 4196, NULL, '명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__D0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 38.01, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__D0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.06, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S1-02__D0004', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 7.91, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S3-02__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 134400, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S3-02__R0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 4196, NULL, '명', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_S3-02__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 32.03, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_S3-02__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 1764, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S3-02__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 1270, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_S3-02__D0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 72, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_AP-E-06__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1968000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-E-06__R0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 8200000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_AP-E-06__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 24, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_AP-E-06__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 520000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-E-06__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 28808000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-S-01__Q0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 4, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-S-01__Q0002', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-S-01__EVT0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2022년 전동화 모듈, 섀시 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_B_SUB_KR_AP-S-01__Q0003', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 10, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-S-01__Q0004', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 7, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_B_SUB_KR_AP-S-01__D0001', 2022, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 70, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2023-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_G0-01__QL0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'C_SUB_EU는 유럽 고객사 대응과 현지 생산을 담당하는 EU 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL);

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2022_C_SUB_EU_G0-01__QL0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 고객 맞춤형 모듈 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_G0-02__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 3800000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_G0-02__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 182400000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_G0-03__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 5, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_G0-03__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_G0-03__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 5, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_G0-05__QL0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2022.01.01~2022.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_G0-05__QL0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, 'EU 생산법인, 품질지원 거점, 판매법인을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_E1-05__QL0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_E1-05__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 16520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-05__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 11400, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-06__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 14000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-06__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 10000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-06__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 24000, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-06__D0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', NULL, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-06__D0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', NULL, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-07__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 42000, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-07__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 7560, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_E1-07__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 18, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-04__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 120, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-04__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 86, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-04__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 71.67, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-04__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 13, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-05__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 29, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-05__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 20, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S6-05__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 68.97, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0004', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0005', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0006', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0007', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0008', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0009', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0010', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0011', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0012', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0013', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0014', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0015', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0016', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0017', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0018', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0019', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0020', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0021', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 88, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0022', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0023', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 250, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0024', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 34, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0025', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 214, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0026', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 29, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0027', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 140, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0028', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 19, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0029', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 44, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0030', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0031', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 54, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0032', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0033', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 153, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0034', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0035', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 131, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0036', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0037', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 86, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0038', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0039', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0040', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0041', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0042', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0043', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0044', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0045', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0046', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0047', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0048', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0049', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0050', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0051', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0052', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0053', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0054', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0055', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0056', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0057', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0058', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0059', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__Q0060', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1501, NULL, '명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__D0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 38.04, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__D0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.01, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S1-02__D0004', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 94.94, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S3-02__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 53760, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S3-02__R0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1501, NULL, '명', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_S3-02__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 35.82, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_S3-02__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 630, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S3-02__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 454, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_S3-02__D0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 72.06, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_AP-E-06__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1102000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-E-06__R0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 3800000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_AP-E-06__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 29, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_AP-E-06__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 310000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-E-06__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 17174000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-S-01__Q0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-S-01__Q0002', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-S-01__EVT0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2022년 전동화 부품, 고객 맞춤형 모듈 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_C_SUB_EU_AP-S-01__Q0003', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 6, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-S-01__Q0004', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 4, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_C_SUB_EU_AP-S-01__D0001', 2022, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 66.67, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2023-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_G0-01__QL0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'D_SUB_US는 북미 생산과 고객지원 기능을 담당하는 미국 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_G0-01__QL0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 서비스 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_G0-02__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 4600000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_G0-02__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 239200000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_G0-03__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_G0-03__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_G0-03__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_G0-05__QL0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2022.01.01~2022.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_G0-05__QL0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '미국 생산법인, 고객지원 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_E1-05__QL0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_E1-05__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 20060, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-05__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 13680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-06__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 17000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-06__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 12000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-06__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 29000, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-06__D0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', NULL, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-06__D0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', NULL, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-07__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 52000, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-07__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 5200, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_E1-07__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 10, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-04__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 140, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-04__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 101, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-04__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 72.14, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-04__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 15, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-05__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 33, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-05__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 22, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S6-05__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 66.67, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0004', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0005', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0006', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0007', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0008', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0009', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0010', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0011', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0012', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0013', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0014', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0015', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0016', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0017', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0018', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0019', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0020', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0021', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0022', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0023', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 24, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0024', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0025', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0026', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0027', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0028', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0029', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0030', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0031', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0032', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0033', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0034', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0035', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0036', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0037', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0038', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0039', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0040', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0041', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 107, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0042', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0043', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 302, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0044', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 41, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0045', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 258, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0046', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 35, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0047', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 169, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0048', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 23, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0049', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 53, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0050', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0051', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 65, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0052', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0053', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 185, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0054', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 25, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0055', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 158, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0056', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0057', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 103, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0058', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0059', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 33, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__Q0060', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1850, NULL, '명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__D0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 38.05, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__D0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.05, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S1-02__D0004', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 94.97, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S3-02__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 63936, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S3-02__R0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1850, NULL, '명', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_S3-02__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 34.56, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_S3-02__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 777, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S3-02__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 559, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_S3-02__D0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 71.94, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_AP-E-06__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1012000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-E-06__R0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 4600000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_AP-E-06__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 22, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_AP-E-06__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 370000, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-E-06__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 20498000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-S-01__Q0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-S-01__Q0002', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-S-01__EVT0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2022년 전동화 부품, 서비스 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2022_D_SUB_US_AP-S-01__Q0003', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 8, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-S-01__Q0004', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 6, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2022_D_SUB_US_AP-S-01__D0001', 2022, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 75, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2023-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_G0-01__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 자동차 부품과 전동화 부품 사업을 총괄하는 지주회사로, 국내외 자회사와 함께 모빌리티 부품 사업을 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-01__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-02__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 1266000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-02__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 88620000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-03__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-03__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-03__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-04__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0001', 'Upstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Upstream 단계에서는 원재료 조달, 부품 가공, 협력사 생산 활동을 포함하며 공급망 환경·인권 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-04__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0002', 'Own operation 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Own operation 단계에서는 본사, 연구소, 생산거점의 제조·품질·환경안전 활동을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-04__QL0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0003', 'Downstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Downstream 단계에서는 고객사 납품, 제품 사용, 서비스 부품 공급과 관련한 품질·안전·환경성과를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-05__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2023.01.01~2023.12.31', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-05__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0002', '자회사 공시 범위', '정성', 'INPUT', 'QL', NULL, '연결 공시 범위에는 A_GROUP 본인 사업장과 B_SUB_KR, C_SUB_EU, D_SUB_US를 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-05__QL0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '본사, 국내 연구소, 그룹 관리 조직 및 일부 지원 거점을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-05__QL0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0004', '보고경계 산정 기준', '정성', 'INPUT', 'QL', NULL, '보고경계는 연결 재무 기준과 ESG 데이터 관리 범위를 함께 고려하며, 자회사 승인값은 롤업 요청 후 연결 기준으로 반영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_G0-06__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-06', '연결 범위', 'G0-06__QL0001', '연결 자회사 범위', '정성', 'INPUT', 'QL', NULL, '연결 범위는 지주사 A_GROUP과 국내 자회사 B_SUB_KR, EU 자회사 C_SUB_EU, 미국 자회사 D_SUB_US로 구성한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0001', '온실가스 감축 목표 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 2045년 탄소중립과 2040년 재생에너지 100% 전환을 목표로 Scope 1·2 배출 감축과 전환계획을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 10620, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 7410, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__QL0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0003', '목표연도', '정성', 'INPUT', 'QL', NULL, '2045', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0003', '감축 목표율', '정량', 'INPUT', 'Q', 100, NULL, '%', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__QL0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0004', '전환계획 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 조달, 고효율 설비 전환, 생산공정 에너지 효율화, 자회사별 감축 과제 점검을 전환계획의 주요 이행수단으로 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__QL0005', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0005', '경영진 KPI 연계 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 전환율과 온실가스 감축 실적을 경영진 KPI에 연계하여 연 단위로 이행 현황을 점검한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-05__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0001', '기후전략 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-E1-001 A_GROUP 기후전략 및 온실가스 관리 규정', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2023_A_GROUP_E1-05__EV0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0002', '기후전략 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '기후전략 문서는 탄소중립 목표, 기준연도, Scope 1·2 감축관리, 재생에너지 전환 KPI 및 경영진 보고 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2023_A_GROUP_E1-06__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 8685, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-06__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 6208, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-06__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 14893, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_E1-06__D0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 607, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_E1-06__D0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 3.92, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_E1-07__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 25625, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-07__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 2562, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_E1-07__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 10, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S6-01__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-01', '공급망 리스크 관리', 'S6-01__QL0001', '공급망 리스크 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 주요 협력사의 환경·인권·윤리 리스크가 조달 안정성과 브랜드 신뢰에 미치는 영향을 고려해 공급망 지속가능성 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-02__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__QL0001', '공급망 실사 체계 설명', '정성', 'INPUT', 'QL', NULL, '공급망 실사는 사전평가, 현장진단, 고위험 협력사 식별, CAP 부여 및 구매정책 반영의 순서로 운영된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다');

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2023_A_GROUP_S6-04__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 65, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-04__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 51, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-04__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 78.46, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S6-04__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 6, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-05__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 13, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-05__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 10, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-05__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 76.92, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S6-05__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__QL0001', '진단 결과 구매정책 반영 설명', '정성', 'INPUT', 'QL', NULL, '진단 결과는 고위험 협력사 개선계획과 구매정책 검토에 반영되며, CAP 이행 현황은 정기적으로 모니터링한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S6-02__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__EV0001', '공급망 실사 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S6-001 공급망 ESG 실사 및 CAP 운영 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2023_A_GROUP_S6-05__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__EV0001', '공급망 CAP 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '공급망 절차서는 협력사 진단 범위, 감사 기준, CAP 이행관리, 결과의 구매정책 반영 기준을 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2023_A_GROUP_S1-02__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 41, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 117, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0005', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 100, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0006', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0007', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 65, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0008', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0009', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0010', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0011', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 25, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0012', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0013', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 72, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0014', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0015', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 61, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0016', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0017', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 40, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0018', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0019', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0020', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0021', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0022', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0023', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 23, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0024', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0025', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0026', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0027', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0028', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0029', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0030', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0031', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0032', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0033', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0034', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0035', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0036', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0037', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0038', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0039', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0040', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0041', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0042', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0043', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0044', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0045', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0046', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0047', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0048', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0049', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0050', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0051', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0052', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0053', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0054', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0055', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0056', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0057', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0058', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0059', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__Q0060', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S1-02__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 841, NULL, '명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S1-02__D0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.81, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S1-02__D0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 87.99, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S1-02__D0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 24.97, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_A_GROUP_S3-01__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0001', '역량개발 중요성', '정성', 'INPUT', 'QL', NULL, '전동화·자율주행·디지털화 전환에 대응하기 위해 미래 모빌리티 기술 인재 확보와 내부 역량 강화가 중요하다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-01__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0002', '교육 전략', '정성', 'INPUT', 'QL', NULL, '직무별 모듈형 교육과 핵심기술 교육을 통해 연구개발, 소프트웨어, 친환경 기술 역량을 강화한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-01__QL0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0003', 'SW아카데미 설명', '정성', 'INPUT', 'QL', NULL, 'SW아카데미는 연구개발 및 소프트웨어 직무 인력을 대상으로 실무 프로젝트 기반 교육을 제공한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-01__QL0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0004', '글로벌 전문가 과정 설명', '정성', 'INPUT', 'QL', NULL, '글로벌 전문가 과정은 해외법인과 글로벌 고객 대응 인력의 사업 수행 역량을 강화하는 프로그램이다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-02__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 30888, NULL, '시간', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-02__R0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 841, NULL, '명', 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_S3-02__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 36.73, NULL, '시간/명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_S3-02__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 378, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-02__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 303, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_S3-02__D0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 80.16, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_S3-01__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0001', '교육관리 지침 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S3-001 교육훈련 및 역량개발 운영 지침', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_S3-01__EV0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0002', '교육관리 지침 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '교육관리 지침은 교육 프로그램 분류, 대상자 관리, 수료 기준, 교육시간 산정 및 성과 모니터링 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-E-06__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0001', '제품 환경 영향 설명', '정성', 'INPUT', 'QL', NULL, '전동화 부품과 경량화·고효율 부품은 제품 사용 단계의 온실가스 감축과 환경영향 저감에 기여한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-E-06__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0002', '저탄소 제품 포트폴리오 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 전동화 부품, 배출저감 기여 부품, 경량화 부품을 중심으로 저탄소 제품 포트폴리오를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-E-06__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 236995200000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-E-06__R0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 1266000000000, NULL, 'KRW', 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-E-06__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 18.72, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-E-06__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 48150, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-E-06__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 2667510000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-E-06__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0001', '친환경 제품·LCA 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APE-001 친환경 제품 및 LCA 관리 기준', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-E-06__EV0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0002', '친환경 제품·LCA 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '친환경 제품 기준은 제품군별 환경성과, 회피 배출량 산정 방법, LCA 검토 절차와 성과관리 지표를 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-S-01__QL0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0001', '제품안전 중요성', '정성', 'INPUT', 'QL', NULL, '제품 품질과 안전은 고객 신뢰, 규제 대응, 필드 리스크 관리에 직접 연결되는 핵심 주제다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__QL0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0002', '제품안전 관리체계', '정성', 'INPUT', 'QL', NULL, '제품안전 관리체계는 설계 검증, 양산 품질관리, 고객사 필드이슈 접수, 원인분석 및 CAP 이행으로 구성된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__QL0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0003', '품질 인증 설명', '정성', 'INPUT', 'QL', NULL, '주요 제품군은 품질 인증과 안전성 평가를 통해 출하 전 검증 절차를 거치며, 고위험 이슈는 별도 심의체계로 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__Q0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__Q0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 0, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__EVT0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2023년 전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__Q0003', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__Q0004', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2023_A_GROUP_AP-S-01__D0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 66.67, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-S-01__EV0001', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0001', '제품안전·품질·리콜 절차서 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APS-001 제품안전·품질·리콜 관리 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_A_GROUP_AP-S-01__EV0002', 2023, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0002', '제품안전·품질·리콜 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '제품안전 절차서는 필드액션, 리콜, 시정조치, 예방조치 및 고객사 보고 기준을 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_G0-01__QL0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'B_SUB_KR은 국내 생산과 연구개발을 담당하는 자동차 부품 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_G0-01__QL0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 모듈, 섀시 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_G0-02__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 8651000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_G0-02__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 475805000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_G0-03__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 8, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_G0-03__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 8, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_G0-03__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_G0-05__QL0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2023.01.01~2023.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_G0-05__QL0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '국내 생산공장, 연구개발 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_E1-05__QL0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_E1-05__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 30680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-05__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 20520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-06__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 25090, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-06__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 17190, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-06__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 42280, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-06__D0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 1720, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-06__D0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 3.91, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-07__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 94300, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-07__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 8487, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_E1-07__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 9, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-04__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 281, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-04__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 222, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-04__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 79, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-04__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 27, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-05__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 59, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-05__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 45, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S6-05__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 76.27, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 259, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 35, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 735, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0004', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 100, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0005', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 627, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0006', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 85, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0007', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 411, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0008', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 56, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0009', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 130, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0010', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0011', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 159, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0012', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0013', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 450, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0014', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 61, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0015', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 384, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0016', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 52, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0017', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 252, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0018', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 34, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0019', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 79, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0020', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0021', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0022', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0023', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 32, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0024', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0025', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0026', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0027', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0028', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0029', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0030', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0031', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0032', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0033', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0034', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0035', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0036', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0037', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0038', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0039', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0040', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0041', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0042', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0043', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 32, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0044', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0045', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0046', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0047', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0048', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0049', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0050', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0051', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0052', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0053', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0054', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0055', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0056', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0057', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0058', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0059', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__Q0060', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 4304, NULL, '명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__D0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.96, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__D0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.06, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S1-02__D0004', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 7.99, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S3-02__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 150675, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S3-02__R0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 4304, NULL, '명', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_S3-02__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 35.01, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_S3-02__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 1937, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S3-02__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 1550, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_S3-02__D0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 80.02, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_AP-E-06__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 2159289600000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-E-06__R0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 8651000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_AP-E-06__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 24.96, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_AP-E-06__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 556400, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-E-06__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 30824560000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-S-01__Q0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 4, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-S-01__Q0002', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-S-01__EVT0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2023년 전동화 모듈, 섀시 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_B_SUB_KR_AP-S-01__Q0003', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 10, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-S-01__Q0004', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 8, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_B_SUB_KR_AP-S-01__D0001', 2023, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 80, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2024-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_G0-01__QL0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'C_SUB_EU는 유럽 고객사 대응과 현지 생산을 담당하는 EU 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_G0-01__QL0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 고객 맞춤형 모듈 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_G0-02__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 4009000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_G0-02__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 192432000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_G0-03__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 5, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_G0-03__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_G0-03__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 5, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_G0-05__QL0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2023.01.01~2023.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_G0-05__QL0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, 'EU 생산법인, 품질지원 거점, 판매법인을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_E1-05__QL0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_E1-05__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 16520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-05__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 11400, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-06__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 13510, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-06__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 9550, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-06__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 23060, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-06__D0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 940, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-06__D0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 3.92, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-07__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 43050, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-07__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 10762, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_E1-07__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 25, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-04__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 130, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-04__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 103, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-04__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 79.23, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-04__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 12, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-05__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 26, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-05__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 20, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S6-05__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 76.92, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0004', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0005', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0006', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0007', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0008', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0009', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL);

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2023_C_SUB_EU_S1-02__Q0010', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0011', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0012', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0013', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0014', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0015', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0016', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0017', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0018', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0019', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0020', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0021', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 91, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0022', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0023', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 257, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0024', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 35, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0025', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 219, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0026', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 30, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0027', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 143, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0028', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0029', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 45, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0030', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0031', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 56, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0032', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0033', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 157, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0034', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0035', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 134, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0036', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0037', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 88, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0038', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0039', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 28, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0040', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0041', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0042', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0043', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0044', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0045', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0046', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0047', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0048', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0049', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0050', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0051', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0052', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0053', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0054', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0055', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0056', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0057', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0058', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0059', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__Q0060', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1538, NULL, '명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__D0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.97, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__D0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.04, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S1-02__D0004', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 94.99, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S3-02__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 60270, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S3-02__R0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1538, NULL, '명', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_S3-02__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 39.19, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_S3-02__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 692, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S3-02__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 553, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_S3-02__D0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 79.91, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_AP-E-06__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1209114400000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-E-06__R0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 4009000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_AP-E-06__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 30.16, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_AP-E-06__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 331700, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-E-06__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 18376180000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-S-01__Q0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-S-01__Q0002', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-S-01__EVT0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2023년 전동화 부품, 고객 맞춤형 모듈 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_C_SUB_EU_AP-S-01__Q0003', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 6, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-S-01__Q0004', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 5, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_C_SUB_EU_AP-S-01__D0001', 2023, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 83.33, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2024-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_G0-01__QL0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'D_SUB_US는 북미 생산과 고객지원 기능을 담당하는 미국 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_G0-01__QL0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 서비스 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_G0-02__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 4853000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_G0-02__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 252356000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_G0-03__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_G0-03__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_G0-03__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_G0-05__QL0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2023.01.01~2023.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_G0-05__QL0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '미국 생산법인, 고객지원 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_E1-05__QL0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_E1-05__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 20060, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-05__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 13680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-06__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 16405, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-06__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 11460, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-06__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 27865, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-06__D0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 1135, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-06__D0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 3.91, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-07__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 53300, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-07__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 7995, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_E1-07__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 15, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-04__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 151, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-04__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 119, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-04__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 78.81, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-04__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 14, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-05__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 31, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-05__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 24, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S6-05__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 77.42, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0004', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0005', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0006', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0007', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0008', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0009', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0010', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0011', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0012', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0013', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0014', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0015', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0016', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0017', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0018', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0019', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0020', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0021', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0022', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0023', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 25, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0024', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0025', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0026', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0027', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0028', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0029', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0030', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0031', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0032', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0033', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0034', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0035', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0036', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0037', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0038', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0039', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0040', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0041', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 109, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0042', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0043', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 310, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0044', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 42, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0045', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 264, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0046', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 36, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0047', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 173, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0048', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 24, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0049', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 55, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0050', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0051', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 67, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0052', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0053', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 190, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0054', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 26, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0055', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 162, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0056', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0057', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 106, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0058', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0059', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 33, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__Q0060', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1896, NULL, '명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__D0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.97, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__D0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.08, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S1-02__D0004', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 95.04, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S3-02__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 71678, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S3-02__R0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1896, NULL, '명', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_S3-02__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 37.8, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_S3-02__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 853, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S3-02__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 683, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_S3-02__D0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 80.07, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_AP-E-06__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1110366400000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-E-06__R0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 4853000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_AP-E-06__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 22.88, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_AP-E-06__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 395900, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-E-06__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 21932860000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-S-01__Q0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-S-01__Q0002', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-S-01__EVT0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2023년 전동화 부품, 서비스 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2023_D_SUB_US_AP-S-01__Q0003', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 8, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-S-01__Q0004', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 6, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2023_D_SUB_US_AP-S-01__D0001', 2023, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 75, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2024-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_G0-01__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 자동차 부품과 전동화 부품 사업을 총괄하는 지주회사로, 국내외 자회사와 함께 모빌리티 부품 사업을 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-01__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-02__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 1332000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-02__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 93240000000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-03__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-03__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 3, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-03__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-04__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0001', 'Upstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Upstream 단계에서는 원재료 조달, 부품 가공, 협력사 생산 활동을 포함하며 공급망 환경·인권 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-04__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0002', 'Own operation 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Own operation 단계에서는 본사, 연구소, 생산거점의 제조·품질·환경안전 활동을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-04__QL0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-04', '가치사슬', 'G0-04__QL0003', 'Downstream 가치사슬 설명', '정성', 'INPUT', 'QL', NULL, 'Downstream 단계에서는 고객사 납품, 제품 사용, 서비스 부품 공급과 관련한 품질·안전·환경성과를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-05__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2024.01.01~2024.12.31', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-05__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0002', '자회사 공시 범위', '정성', 'INPUT', 'QL', NULL, '연결 공시 범위에는 A_GROUP 본인 사업장과 B_SUB_KR, C_SUB_EU, D_SUB_US를 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-05__QL0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '본사, 국내 연구소, 그룹 관리 조직 및 일부 지원 거점을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-05__QL0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0004', '보고경계 산정 기준', '정성', 'INPUT', 'QL', NULL, '보고경계는 연결 재무 기준과 ESG 데이터 관리 범위를 함께 고려하며, 자회사 승인값은 롤업 요청 후 연결 기준으로 반영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_G0-06__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-06', '연결 범위', 'G0-06__QL0001', '연결 자회사 범위', '정성', 'INPUT', 'QL', NULL, '연결 범위는 지주사 A_GROUP과 국내 자회사 B_SUB_KR, EU 자회사 C_SUB_EU, 미국 자회사 D_SUB_US로 구성한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0001', '온실가스 감축 목표 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 2045년 탄소중립과 2040년 재생에너지 100% 전환을 목표로 Scope 1·2 배출 감축과 전환계획을 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 10620, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 7410, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__QL0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0003', '목표연도', '정성', 'INPUT', 'QL', NULL, '2045', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0003', '감축 목표율', '정량', 'INPUT', 'Q', 100, NULL, '%', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__QL0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0004', '전환계획 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 조달, 고효율 설비 전환, 생산공정 에너지 효율화, 자회사별 감축 과제 점검을 전환계획의 주요 이행수단으로 운영한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__QL0005', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0005', '경영진 KPI 연계 설명', '정성', 'INPUT', 'QL', NULL, '재생에너지 전환율과 온실가스 감축 실적을 경영진 KPI에 연계하여 연 단위로 이행 현황을 점검한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-05__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0001', '기후전략 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-E1-001 A_GROUP 기후전략 및 온실가스 관리 규정', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2024_A_GROUP_E1-05__EV0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__EV0002', '기후전략 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '기후전략 문서는 탄소중립 목표, 기준연도, Scope 1·2 감축관리, 재생에너지 전환 KPI 및 경영진 보고 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2024_A_GROUP_E1-06__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 8270, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-06__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 5795, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-06__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 14065, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_E1-06__D0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 828, NULL, 'tCO2eq', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_E1-06__D0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 5.56, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_E1-07__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 26250, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-07__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 3675, NULL, 'MWh', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_E1-07__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 14, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S6-01__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-01', '공급망 리스크 관리', 'S6-01__QL0001', '공급망 리스크 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 주요 협력사의 환경·인권·윤리 리스크가 조달 안정성과 브랜드 신뢰에 미치는 영향을 고려해 공급망 지속가능성 리스크를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-02__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__QL0001', '공급망 실사 체계 설명', '정성', 'INPUT', 'QL', NULL, '공급망 실사는 사전평가, 현장진단, 고위험 협력사 식별, CAP 부여 및 구매정책 반영의 순서로 운영된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-04__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 70, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-04__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 60, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-04__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 85.71, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S6-04__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 6, NULL, '개사', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-05__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 13, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-05__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 11, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-05__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 84.62, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S6-05__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__QL0001', '진단 결과 구매정책 반영 설명', '정성', 'INPUT', 'QL', NULL, '진단 결과는 고위험 협력사 개선계획과 구매정책 검토에 반영되며, CAP 이행 현황은 정기적으로 모니터링한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S6-02__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-02', '공급망 실사 체계', 'S6-02__EV0001', '공급망 실사 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S6-001 공급망 ESG 실사 및 CAP 운영 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2024_A_GROUP_S6-05__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__EV0001', '공급망 CAP 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '공급망 절차서는 협력사 진단 범위, 감사 기준, CAP 이행관리, 결과의 구매정책 반영 기준을 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', NULL),
('F_2024_A_GROUP_S1-02__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 42, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 120, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0005', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 102, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0006', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0007', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 67, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0008', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0009', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 21, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0010', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0011', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 26, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0012', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0013', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 73, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0014', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0015', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 63, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0016', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0017', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 41, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0018', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0019', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0020', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0021', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0022', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0023', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 24, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0024', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0025', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다');

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2024_A_GROUP_S1-02__Q0026', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0027', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0028', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0029', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0030', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0031', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0032', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0033', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0034', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0035', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0036', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0037', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0038', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0039', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0040', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0041', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0042', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0043', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 16, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0044', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0045', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0046', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0047', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0048', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0049', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0050', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0051', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0052', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0053', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0054', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0055', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0056', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0057', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0058', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0059', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__Q0060', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S1-02__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 861, NULL, '명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S1-02__D0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 38.1, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S1-02__D0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 87.92, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S1-02__D0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 24.85, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_A_GROUP_S3-01__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0001', '역량개발 중요성', '정성', 'INPUT', 'QL', NULL, '전동화·자율주행·디지털화 전환에 대응하기 위해 미래 모빌리티 기술 인재 확보와 내부 역량 강화가 중요하다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-01__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0002', '교육 전략', '정성', 'INPUT', 'QL', NULL, '직무별 모듈형 교육과 핵심기술 교육을 통해 연구개발, 소프트웨어, 친환경 기술 역량을 강화한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-01__QL0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0003', 'SW아카데미 설명', '정성', 'INPUT', 'QL', NULL, 'SW아카데미는 연구개발 및 소프트웨어 직무 인력을 대상으로 실무 프로젝트 기반 교육을 제공한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-01__QL0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__QL0004', '글로벌 전문가 과정 설명', '정성', 'INPUT', 'QL', NULL, '글로벌 전문가 과정은 해외법인과 글로벌 고객 대응 인력의 사업 수행 역량을 강화하는 프로그램이다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-02__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 34354, NULL, '시간', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-02__R0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 861, NULL, '명', 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_S3-02__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 39.9, NULL, '시간/명', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_S3-02__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 413, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-02__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 364, NULL, '명', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_S3-02__D0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 88.14, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_S3-01__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0001', '교육관리 지침 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-S3-001 교육훈련 및 역량개발 운영 지침', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_S3-01__EV0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-01', '교육·역량개발 체계', 'S3-01__EV0002', '교육관리 지침 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '교육관리 지침은 교육 프로그램 분류, 대상자 관리, 수료 기준, 교육시간 산정 및 성과 모니터링 절차를 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-E-06__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0001', '제품 환경 영향 설명', '정성', 'INPUT', 'QL', NULL, '전동화 부품과 경량화·고효율 부품은 제품 사용 단계의 온실가스 감축과 환경영향 저감에 기여한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-E-06__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__QL0002', '저탄소 제품 포트폴리오 설명', '정성', 'INPUT', 'QL', NULL, 'A_GROUP은 전동화 부품, 배출저감 기여 부품, 경량화 부품을 중심으로 저탄소 제품 포트폴리오를 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-E-06__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 258940800000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-E-06__R0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 1332000000000, NULL, 'KRW', 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-E-06__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 19.44, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-E-06__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 51300, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-E-06__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 2842020000, NULL, 'KRW', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-E-06__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0001', '친환경 제품·LCA 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APE-001 친환경 제품 및 LCA 관리 기준', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-E-06__EV0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__EV0002', '친환경 제품·LCA 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '친환경 제품 기준은 제품군별 환경성과, 회피 배출량 산정 방법, LCA 검토 절차와 성과관리 지표를 포함한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-S-01__QL0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0001', '제품안전 중요성', '정성', 'INPUT', 'QL', NULL, '제품 품질과 안전은 고객 신뢰, 규제 대응, 필드 리스크 관리에 직접 연결되는 핵심 주제다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__QL0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0002', '제품안전 관리체계', '정성', 'INPUT', 'QL', NULL, '제품안전 관리체계는 설계 검증, 양산 품질관리, 고객사 필드이슈 접수, 원인분석 및 CAP 이행으로 구성된다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__QL0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__QL0003', '품질 인증 설명', '정성', 'INPUT', 'QL', NULL, '주요 제품군은 품질 인증과 안전성 평가를 통해 출하 전 검증 절차를 거치며, 고위험 이슈는 별도 심의체계로 관리한다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'GROUP_POLICY', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__Q0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__Q0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 0, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__EVT0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2024년 전동화 부품, 섀시·안전 부품, 모듈 부품, 서비스 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__Q0003', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__Q0004', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', 'A_GROUP도 본인 ENTITY 값을 입력한다'),
('F_2024_A_GROUP_AP-S-01__D0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 100, NULL, '%', 'calculated', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-S-01__EV0001', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0001', '제품안전·품질·리콜 절차서 문서명', '정성', 'REFERENCE', 'EV', NULL, 'DOC-APS-001 제품안전·품질·리콜 관리 절차서', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_A_GROUP_AP-S-01__EV0002', 2024, 'A_GROUP', 'A_GROUP 지주사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EV0002', '제품안전·품질·리콜 근거 요약', '정성', 'REFERENCE', 'EV', NULL, '제품안전 절차서는 필드액션, 리콜, 시정조치, 예방조치 및 고객사 보고 기준을 정의한다.', NULL, 'reference', 'approved', 'U_ESG_MANAGER_A', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_G0-01__QL0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'B_SUB_KR은 국내 생산과 연구개발을 담당하는 자동차 부품 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_G0-01__QL0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 모듈, 섀시 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_G0-02__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 9102000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_G0-02__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 500610000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_G0-03__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 9, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_G0-03__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 9, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_G0-03__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_G0-05__QL0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2024.01.01~2024.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_G0-05__QL0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '국내 생산공장, 연구개발 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_E1-05__QL0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_E1-05__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 30680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-05__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 20520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-06__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 24180, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-06__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 16380, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-06__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 40560, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-06__D0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 1720, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-06__D0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 4.07, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-07__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 96600, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-07__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 11592, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_E1-07__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 12, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-04__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 302, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-04__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 260, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-04__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 86.09, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-04__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 24, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-05__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 53, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-05__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 45, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S6-05__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 84.91, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 266, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 36, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 753, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0004', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 103, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0005', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 642, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0006', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 88, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0007', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 421, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0008', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 57, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0009', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 133, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0010', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0011', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 163, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0012', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0013', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 461, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0014', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 63, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0015', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 393, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0016', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 54, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0017', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 258, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0018', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 35, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0019', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 81, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0020', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0021', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0022', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0023', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 33, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0024', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0025', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 28, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0026', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0027', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0028', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0029', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0030', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0031', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0032', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0033', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0034', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0035', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0036', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0037', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0038', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0039', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0040', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0041', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0042', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0043', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 33, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0044', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0045', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 28, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0046', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0047', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0048', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0049', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0050', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0051', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 7, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0052', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0053', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0054', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0055', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 17, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0056', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0057', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0058', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0059', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__Q0060', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 4412, NULL, '명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__D0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.96, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__D0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88.01, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S1-02__D0004', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 8.02, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S3-02__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 167580, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S3-02__R0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 4412, NULL, '명', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_S3-02__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 37.98, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_S3-02__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 2117, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S3-02__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 1863, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_S3-02__D0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 88, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_AP-E-06__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 2359238400000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-E-06__R0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 9102000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_AP-E-06__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 25.92, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_AP-E-06__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 592800, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-E-06__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 32841120000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-S-01__Q0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 3, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-S-01__Q0002', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-S-01__EVT0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2024년 전동화 모듈, 섀시 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_B_SUB_KR_AP-S-01__Q0003', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 9, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-S-01__Q0004', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 8, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_B_SUB_KR_AP-S-01__D0001', 2024, 'B_SUB_KR', 'B_SUB_KR 국내 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 88.89, NULL, '%', 'calculated', 'approved', 'U_MANAGER_B_SUB_KR', '2025-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_G0-01__QL0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'C_SUB_EU는 유럽 고객사 대응과 현지 생산을 담당하는 EU 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_G0-01__QL0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 고객 맞춤형 모듈 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_G0-02__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 4218000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_G0-02__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 202464000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_G0-03__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_G0-03__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_G0-03__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_G0-05__QL0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2024.01.01~2024.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_G0-05__QL0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, 'EU 생산법인, 품질지원 거점, 판매법인을 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_E1-05__QL0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_E1-05__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 16520, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-05__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 11400, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-06__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 13020, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-06__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 9100, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-06__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 22120, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-06__D0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 940, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-06__D0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 4.08, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-07__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 44100, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-07__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 14994, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_E1-07__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 34, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-04__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 139, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-04__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 120, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-04__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 86.33, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-04__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 11, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-05__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 24, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-05__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 20, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S6-05__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 83.33, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0004', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0005', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0006', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0007', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0008', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0009', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0010', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0011', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0012', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0013', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0014', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0015', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0016', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0017', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0018', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0019', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0020', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0021', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 93, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0022', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0023', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 263, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0024', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 36, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0025', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 224, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0026', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 31, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0027', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 147, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0028', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 20, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0029', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 46, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0030', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0031', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 57, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0032', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0033', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 161, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0034', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0035', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 137, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0036', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 19, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0037', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 90, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0038', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0039', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 28, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0040', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0041', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0042', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0043', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0044', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL);

INSERT INTO TMP_ESG_DUMMY_INPUT_FACT VALUES
('F_2024_C_SUB_EU_S1-02__Q0045', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 12, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0046', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0047', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0048', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0049', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0050', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0051', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0052', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0053', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0054', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0055', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0056', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0057', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0058', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0059', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__Q0060', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1575, NULL, '명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__D0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 37.97, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__D0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 88, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S1-02__D0004', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 94.98, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S3-02__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 67032, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S3-02__R0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1575, NULL, '명', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_S3-02__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 42.56, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_S3-02__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 756, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S3-02__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 665, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_S3-02__D0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 87.96, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_AP-E-06__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1321077600000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-E-06__R0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 4218000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_AP-E-06__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 31.32, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_AP-E-06__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 353400, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-E-06__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 19578360000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-S-01__Q0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-S-01__Q0002', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 0, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-S-01__EVT0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2024년 전동화 부품, 고객 맞춤형 모듈 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_C_SUB_EU_AP-S-01__Q0003', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 5, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-S-01__Q0004', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 4, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_C_SUB_EU_AP-S-01__D0001', 2024, 'C_SUB_EU', 'C_SUB_EU EU 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 80, NULL, '%', 'calculated', 'approved', 'U_MANAGER_C_SUB_EU', '2025-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_G0-01__QL0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0001', '회사 개요', '정성', 'INPUT', 'QL', NULL, 'D_SUB_US는 북미 생산과 고객지원 기능을 담당하는 미국 소재 자회사다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_G0-01__QL0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-01', '회사 개요', 'G0-01__QL0002', '주요 제품·서비스', '정성', 'INPUT', 'QL', NULL, '전동화 부품, 서비스 부품, 안전 부품', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_G0-02__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0001', '매출액', '정량', 'INPUT', 'Q', 5106000000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_G0-02__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-02', '재무 개요', 'G0-02__Q0002', '영업이익', '정량', 'INPUT', 'Q', 265512000000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_G0-03__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0001', '전체 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_G0-03__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0002', '국내 사업장 수', '정량', 'INPUT', 'Q', 0, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_G0-03__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-03', '사업장 현황', 'G0-03__Q0003', '해외 사업장 수', '정량', 'INPUT', 'Q', 6, NULL, '개', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_G0-05__QL0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0001', '보고기간', '정성', 'INPUT', 'QL', NULL, '2024.01.01~2024.12.31', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_G0-05__QL0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '경영일반', '공통 경영일반', 'G0-05', '보고 기준 및 보고 범위', 'G0-05__QL0003', '본인 사업장·공장 범위', '정성', 'INPUT', 'QL', NULL, '미국 생산법인, 고객지원 거점, 물류센터를 본인 사업장 범위로 포함한다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_E1-05__QL0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__QL0002', '기준연도', '정성', 'INPUT', 'QL', NULL, '2019', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_E1-05__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0001', '기준연도 Scope 1 배출량', '정량', 'INPUT', 'Q', 20060, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-05__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-05', '온실가스 감축 목표', 'E1-05__Q0002', '기준연도 Scope 2 배출량', '정량', 'INPUT', 'Q', 13680, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-06__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0001', 'Scope 1 배출량', '정량', 'INPUT', 'Q', 15810, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-06__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__Q0002', 'Scope 2 배출량', '정량', 'INPUT', 'Q', 10920, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-06__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0001', 'Scope 1·2 총배출량', '정량', 'DERIVED', 'Q', 26730, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'E1-06__Q0001;E1-06__Q0002', 'Scope 1 + Scope 2', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-06__D0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0002', '전년 대비 온실가스 감축량', '정량', 'DERIVED', 'Q', 1135, NULL, 'tCO2eq', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'prior_year E1-06__D0001;current_year E1-06__D0001', 'prior year total - current year total', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-06__D0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-06', '온실가스 감축 실적', 'E1-06__D0003', '전년 대비 온실가스 감축률', '정량', 'DERIVED', 'Q', 4.07, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'E1-06__D0002;prior_year E1-06__D0001', 'reduction amount / prior year total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-07__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0001', '총 전력 사용량', '정량', 'INPUT', 'Q', 54600, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-07__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__Q0002', '재생에너지 사용량', '정량', 'INPUT', 'Q', 12012, NULL, 'MWh', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_E1-07__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '기후변화 대응', '기후목표·전환계획', 'E1-07', '재생에너지 전환 실적', 'E1-07__D0001', '재생에너지 전환율', '정량', 'DERIVED', 'Q', 22, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'E1-07__Q0002;E1-07__Q0001', 'renewable energy / total electricity * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-04__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0001', '감사 대상 공급업체 수', '정량', 'INPUT', 'Q', 162, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-04__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0002', '감사 완료 공급업체 수', '정량', 'INPUT', 'Q', 139, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-04__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__D0001', '공급업체 감사 수행률', '정량', 'DERIVED', 'Q', 85.8, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S6-04__Q0002;S6-04__Q0001', 'audit completed / audit target * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-04__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-04', '공급업체 감사 수행', 'S6-04__Q0003', '고위험 공급업체 수', '정량', 'INPUT', 'Q', 13, NULL, '개사', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-05__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0001', '공급망 CAP 전체 건수', '정량', 'INPUT', 'Q', 29, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-05__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__Q0002', '공급망 CAP 완료 건수', '정량', 'INPUT', 'Q', 24, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S6-05__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '공급망 지속가능성 관리', '공급망 감사·시정조치', 'S6-05', '공급업체 CAP 관리', 'S6-05__D0001', '공급망 CAP 완료율', '정량', 'DERIVED', 'Q', 82.76, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S6-05__Q0002;S6-05__Q0001', 'CAP completed / CAP total * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0001', '한국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0002', '한국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0003', '한국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 18, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0004', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0004', '한국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0005', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0005', '한국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0006', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0006', '한국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0007', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0007', '한국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 10, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0008', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0008', '한국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0009', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0009', '한국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0010', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0010', '한국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0011', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0011', '한국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0012', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0012', '한국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0013', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0013', '한국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 11, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0014', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0014', '한국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0015', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0015', '한국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0016', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0016', '한국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0017', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0017', '한국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 6, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0018', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0018', '한국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0019', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0019', '한국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0020', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0020', '한국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0021', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0021', '유럽 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0022', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0022', '유럽 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0023', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0023', '유럽 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 25, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0024', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0024', '유럽 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0025', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0025', '유럽 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 22, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0026', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0026', '유럽 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0027', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0027', '유럽 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 14, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0028', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0028', '유럽 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0029', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0029', '유럽 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 4, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0030', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0030', '유럽 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0031', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0031', '유럽 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0032', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0032', '유럽 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0033', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0033', '유럽 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0034', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0034', '유럽 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0035', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0035', '유럽 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 13, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0036', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0036', '유럽 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 2, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0037', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0037', '유럽 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0038', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0038', '유럽 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 1, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0039', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0039', '유럽 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 3, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0040', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0040', '유럽 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 0, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0041', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0041', '미국 남성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 112, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0042', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0042', '미국 남성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0043', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0043', '미국 남성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 317, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0044', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0044', '미국 남성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 43, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0045', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0045', '미국 남성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 270, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0046', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0046', '미국 남성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 37, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0047', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0047', '미국 남성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 177, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0048', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0048', '미국 남성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 24, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0049', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0049', '미국 남성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 56, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0050', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0050', '미국 남성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 8, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0051', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0051', '미국 여성 20대 정규직 임직원 수', '정량', 'INPUT', 'Q', 69, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0052', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0052', '미국 여성 20대 계약직 임직원 수', '정량', 'INPUT', 'Q', 9, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0053', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0053', '미국 여성 30대 정규직 임직원 수', '정량', 'INPUT', 'Q', 194, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0054', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0054', '미국 여성 30대 계약직 임직원 수', '정량', 'INPUT', 'Q', 27, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0055', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0055', '미국 여성 40대 정규직 임직원 수', '정량', 'INPUT', 'Q', 166, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0056', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0056', '미국 여성 40대 계약직 임직원 수', '정량', 'INPUT', 'Q', 23, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0057', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0057', '미국 여성 50대 정규직 임직원 수', '정량', 'INPUT', 'Q', 109, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0058', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0058', '미국 여성 50대 계약직 임직원 수', '정량', 'INPUT', 'Q', 15, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0059', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0059', '미국 여성 60대 이상 정규직 임직원 수', '정량', 'INPUT', 'Q', 34, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__Q0060', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__Q0060', '미국 여성 60대 이상 계약직 임직원 수', '정량', 'INPUT', 'Q', 5, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0001', '전체 임직원 수', '정량', 'DERIVED', 'Q', 1940, NULL, '명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S1-02__Q0001:Q0060', 'SUM(S1-02__Q0001:Q0060)', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__D0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0002', '여성 임직원 비율', '정량', 'DERIVED', 'Q', 38.09, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S1-02 female Q atoms;S1-02__D0001', '여성 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__D0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0003', '정규직 비율', '정량', 'DERIVED', 'Q', 87.99, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S1-02 regular Q atoms;S1-02__D0001', '정규직 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S1-02__D0004', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S1-02', '임직원 구성', 'S1-02__D0004', '해외 임직원 비율', '정량', 'DERIVED', 'Q', 95.1, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S1-02 EU/US Q atoms;S1-02__D0001', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S3-02__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0001', '총 교육시간', '정량', 'INPUT', 'Q', 79720, NULL, '시간', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S3-02__R0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__R0001', '전체 임직원 수 참조', '정량', 'REFERENCE', 'Q', 1940, NULL, '명', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_S3-02__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0001', '1인당 교육시간', '정량', 'DERIVED', 'Q', 41.09, NULL, '시간/명', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S3-02__Q0001;S3-02__R0001', 'total training hours / employee count', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_S3-02__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0002', '핵심직무 교육 대상 인원', '정량', 'INPUT', 'Q', 932, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S3-02__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__Q0003', '핵심직무 교육 수료 인원', '정량', 'INPUT', 'Q', 821, NULL, '명', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_S3-02__D0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '인적자원 관리', '교육훈련·역량개발', 'S3-02', '교육성과', 'S3-02__D0002', '핵심직무 교육 달성률', '정량', 'DERIVED', 'Q', 88.09, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'S3-02__Q0003;S3-02__Q0002', 'completed / target * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_AP-E-06__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0001', '친환경 제품 매출액', '정량', 'INPUT', 'Q', 1213185600000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-E-06__R0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__R0001', '전체 매출액 참조', '정량', 'REFERENCE', 'Q', 5106000000000, NULL, 'KRW', 'reference', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_AP-E-06__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__D0001', '친환경 제품 매출 비중', '정량', 'DERIVED', 'Q', 23.76, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'AP-E-06__Q0001;AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_AP-E-06__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0002', '회피 배출량', '정량', 'INPUT', 'Q', 421800, NULL, 'tCO2eq', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-E-06__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '자원 사용 및 순환 경제', '저탄소·친환경 제품', 'AP-E-06', '저탄소·친환경 제품', 'AP-E-06__Q0003', '사회적 비용 절감 효과', '정량', 'INPUT', 'Q', 23367720000, NULL, 'KRW', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-S-01__Q0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0001', '필드액션 건수', '정량', 'INPUT', 'Q', 2, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-S-01__Q0002', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0002', '리콜 건수', '정량', 'INPUT', 'Q', 1, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-S-01__EVT0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__EVT0001', '제품안전 event 요약', '정성', 'INPUT', 'EVENT', NULL, '2024년 전동화 부품, 서비스 부품, 안전 부품 관련 필드 이슈를 접수·분류하고 CAP 이행상태를 관리하였다.', NULL, 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'N', NULL),
('F_2024_D_SUB_US_AP-S-01__Q0003', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0003', '제품안전 CAP 전체 건수', '정량', 'INPUT', 'Q', 7, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-S-01__Q0004', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__Q0004', '제품안전 CAP 완료 건수', '정량', 'INPUT', 'Q', 6, NULL, '건', 'manual_input', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', NULL, NULL, 'ENTITY_SOURCE', 'Y', NULL),
('F_2024_D_SUB_US_AP-S-01__D0001', 2024, 'D_SUB_US', 'D_SUB_US 미국 자회사', 'ENTITY', '제품 품질 및 안전 확보', '소비자 건강·제품안전', 'AP-S-01', '제품 안전결함·필드액션·리콜 관리', 'AP-S-01__D0001', '제품안전 CAP 완료율', '정량', 'DERIVED', 'Q', 85.71, NULL, '%', 'calculated', 'approved', 'U_MANAGER_D_SUB_US', '2025-02-15 01:00:00', 'AP-S-01__Q0004;AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'ENTITY_SOURCE', 'N', NULL);



-- 3.1 Onboarding cycles for all company/year combinations in dummy facts
INSERT INTO ESG_ONBOARDING_CYCLE (
    company_id, reporting_year, cycle_name, cycle_status, source_materiality_run_id, created_by_user_id
)
SELECT
    p.company_id,
    t.reporting_year,
    CONCAT(t.company_code, ' ', t.reporting_year, ' ESG 온보딩 사이클'),
    'closed',
    NULL,
    @user_id_esg_admin
FROM (SELECT DISTINCT company_code, reporting_year FROM TMP_ESG_DUMMY_INPUT_FACT) t
JOIN ESG_COMPANY_PROFILE p
  ON p.company_code=t.company_code
ON DUPLICATE KEY UPDATE
    cycle_name=VALUES(cycle_name),
    cycle_status=VALUES(cycle_status),
    source_materiality_run_id=VALUES(source_materiality_run_id),
    created_by_user_id=VALUES(created_by_user_id);

-- 3.2 Metric assignment per company/year/metric
INSERT INTO ESG_METRIC_ASSIGNMENT (
    esg_onboarding_cycle_id, company_id, metric_id, assignee_user_id, assignee_email,
    assignment_status, due_date, created_by_user_id
)
SELECT DISTINCT
    c.id,
    p.company_id,
    t.metric_id,
    @user_id_assignee,
    'assignee@example.com',
    'completed',
    MAKEDATE(t.reporting_year, 1) + INTERVAL 364 DAY,
    @user_id_esg_admin
FROM TMP_ESG_DUMMY_INPUT_FACT t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.company_code
JOIN ESG_ONBOARDING_CYCLE c ON c.company_id=p.company_id AND c.reporting_year=t.reporting_year AND c.cycle_type='regular'
WHERE NOT EXISTS (
    SELECT 1
    FROM ESG_METRIC_ASSIGNMENT a
    WHERE a.esg_onboarding_cycle_id=c.id
      AND a.company_id=p.company_id
      AND a.metric_id=t.metric_id
      AND a.delete_yn=0
);

-- 3.3 Input values
INSERT INTO ESG_ONBOARDING_INPUT_VALUE (
    esg_metric_assignment_id, esg_onboarding_cycle_id, company_id, reporting_year, company_scope_type,
    metric_id, atomic_metric_id, value_numeric, value_text, unit, value_source_type,
    input_status, input_user_id, approved_by_user_id, approved_at
)
SELECT
    (SELECT MIN(a.id)
     FROM ESG_METRIC_ASSIGNMENT a
     WHERE a.esg_onboarding_cycle_id=c.id AND a.company_id=p.company_id AND a.metric_id=t.metric_id AND a.delete_yn=0),
    c.id,
    p.company_id,
    t.reporting_year,
    t.company_scope_type,
    t.metric_id,
    t.atomic_metric_id,
    t.value_numeric,
    t.value_text,
    t.unit,
    COALESCE(t.value_source_type, 'manual_input'),
    COALESCE(t.approval_status, 'approved'),
    @user_id_assignee,
    @user_id_approver,
    t.approved_at
FROM TMP_ESG_DUMMY_INPUT_FACT t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.company_code
JOIN ESG_ONBOARDING_CYCLE c ON c.company_id=p.company_id AND c.reporting_year=t.reporting_year AND c.cycle_type='regular'
ON DUPLICATE KEY UPDATE
    esg_metric_assignment_id=VALUES(esg_metric_assignment_id),
    esg_onboarding_cycle_id=VALUES(esg_onboarding_cycle_id),
    metric_id=VALUES(metric_id),
    value_numeric=VALUES(value_numeric),
    value_text=VALUES(value_text),
    unit=VALUES(unit),
    value_source_type=VALUES(value_source_type),
    input_status=VALUES(input_status),
    approved_by_user_id=VALUES(approved_by_user_id),
    approved_at=VALUES(approved_at);



-- ---------------------------------------------------------------------
-- 3.4 Approval history: submission + approval events, simplified from 3 approval tables
-- ---------------------------------------------------------------------
INSERT INTO ESG_ONBOARDING_APPROVAL_HISTORY (
    esg_onboarding_cycle_id, esg_metric_assignment_id, company_id, reporting_year,
    metric_id, atomic_metric_id, action_type, action_status, actor_user_id, assignee_user_id, comment_text
)
SELECT DISTINCT
    c.id,
    (SELECT MIN(a.id) FROM ESG_METRIC_ASSIGNMENT a WHERE a.esg_onboarding_cycle_id=c.id AND a.company_id=p.company_id AND a.metric_id=t.metric_id AND a.delete_yn=0),
    p.company_id,
    t.reporting_year,
    t.metric_id,
    NULL,
    'submit',
    'submitted',
    @user_id_assignee,
    @user_id_approver,
    'MVP v2 seed submitted'
FROM TMP_ESG_DUMMY_INPUT_FACT t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.company_code
JOIN ESG_ONBOARDING_CYCLE c ON c.company_id=p.company_id AND c.reporting_year=t.reporting_year AND c.cycle_type='regular'
UNION ALL
SELECT DISTINCT
    c.id,
    (SELECT MIN(a.id) FROM ESG_METRIC_ASSIGNMENT a WHERE a.esg_onboarding_cycle_id=c.id AND a.company_id=p.company_id AND a.metric_id=t.metric_id AND a.delete_yn=0),
    p.company_id,
    t.reporting_year,
    t.metric_id,
    NULL,
    'approve',
    'approved',
    @user_id_approver,
    @user_id_assignee,
    'MVP v2 seed approved'
FROM TMP_ESG_DUMMY_INPUT_FACT t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.company_code
JOIN ESG_ONBOARDING_CYCLE c ON c.company_id=p.company_id AND c.reporting_year=t.reporting_year AND c.cycle_type='regular';

-- ---------------------------------------------------------------------
-- 3.5 KPI fact: approved input values become official facts directly
-- ---------------------------------------------------------------------
INSERT INTO ESG_KPI_FACT (
    source_input_value_id, company_id, reporting_year, company_scope_type,
    metric_id, atomic_metric_id, value_numeric, value_text, unit, value_source_type,
    approval_status, approved_by_user_id, approved_at
)
SELECT
    iv.id,
    iv.company_id,
    iv.reporting_year,
    iv.company_scope_type,
    iv.metric_id,
    iv.atomic_metric_id,
    iv.value_numeric,
    iv.value_text,
    iv.unit,
    iv.value_source_type,
    'approved',
    @user_id_approver,
    iv.approved_at
FROM ESG_ONBOARDING_INPUT_VALUE iv
WHERE iv.company_id IN (@company_id_A_GROUP, @company_id_B_SUB_KR, @company_id_C_SUB_EU, @company_id_D_SUB_US)
  AND iv.reporting_year BETWEEN 2022 AND 2024
ON DUPLICATE KEY UPDATE
    source_input_value_id=VALUES(source_input_value_id),
    metric_id=VALUES(metric_id),
    value_numeric=VALUES(value_numeric),
    value_text=VALUES(value_text),
    unit=VALUES(unit),
    value_source_type=VALUES(value_source_type),
    approval_status=VALUES(approval_status),
    approved_by_user_id=VALUES(approved_by_user_id),
    approved_at=VALUES(approved_at);

-- ---------------------------------------------------------------------
-- 4. Calculation rule master/source
-- ---------------------------------------------------------------------
DELETE FROM ESG_CALCULATION_RULE_SOURCE WHERE calculation_rule_code LIKE 'CR_%';

INSERT INTO ESG_CALCULATION_RULE (
    calculation_rule_code, target_atomic_metric_id, target_atomic_name_kr, metric_id, formula_type,
    execution_scope, applicable_company_scope, source_atomic_metric_ids, numerator_atomic_metric_ids,
    denominator_atomic_metric_ids, calculation_formula_label, sql_template, zero_division_policy,
    rounding_policy, result_table, output_unit, execution_order
) VALUES
('CR_AP_E_06_R0001', 'AP-E-06__R0001', '전체 매출액 참조', 'AP-E-06', 'REFERENCE_COPY', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02__Q0001', NULL, NULL, '전체 매출액 참조', 'SELECT
  company_id,
  reporting_year,
  ''AP-E-06__R0001'' AS atomic_metric_id,
  value_numeric,
  value_text,
  ''KRW'' AS unit,
  ''reference_copy'' AS value_source_type,
  approval_status
FROM esg_kpi_fact
WHERE company_id = :company_id
  AND reporting_year = :reporting_year
  AND atomic_metric_id = ''G0-02__Q0001''
  AND approval_status = ''approved'';', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', 'KRW', 10),
('CR_S3_02_R0001', 'S3-02__R0001', '전체 임직원 수 참조', 'S3-02', 'REFERENCE_COPY', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02__D0001', NULL, NULL, '전체 임직원 수 참조', 'SELECT
  company_id,
  reporting_year,
  ''S3-02__R0001'' AS atomic_metric_id,
  value_numeric,
  value_text,
  ''명'' AS unit,
  ''reference_copy'' AS value_source_type,
  approval_status
FROM esg_kpi_fact
WHERE company_id = :company_id
  AND reporting_year = :reporting_year
  AND atomic_metric_id = ''S1-02__D0001''
  AND approval_status = ''approved'';', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '명', 10),
('CR_E1_06_D0001', 'E1-06__D0001', 'Scope 1·2 총배출량', 'E1-06', 'ENTITY_SUM', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06__Q0001;E1-06__Q0002', NULL, NULL, 'Scope 1 + Scope 2', 'SELECT
  :company_id AS company_id,
  :reporting_year AS reporting_year,
  ''E1-06__D0001'' AS atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM esg_kpi_fact
WHERE company_id = :company_id
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-06__Q0001'', ''E1-06__Q0002'')
  AND approval_status = ''approved'';', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', 'tCO2eq', 20),
('CR_S1_02_D0001', 'S1-02__D0001', '전체 임직원 수', 'S1-02', 'ENTITY_SUM', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', NULL, NULL, 'SUM(S1-02__Q0001:Q0060)', 'SELECT
  :company_id AS company_id,
  :reporting_year AS reporting_year,
  ''S1-02__D0001'' AS atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''명'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM esg_kpi_fact
WHERE company_id = :company_id
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
  AND approval_status = ''approved'';', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '명', 20),
('CR_AP_S_01_D0001', 'AP-S-01__D0001', '제품안전 CAP 완료율', 'AP-S-01', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'AP-S-01__Q0004', 'AP-S-01__Q0003', 'completed CAP / total CAP * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''AP-S-01__Q0004'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''AP-S-01__Q0003'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''AP-S-01__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_E1_07_D0001', 'E1-07__D0001', '재생에너지 전환율', 'E1-07', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'E1-07__Q0002', 'E1-07__Q0001', 'renewable energy / total electricity * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''E1-07__Q0002'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''E1-07__Q0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''E1-07__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S1_02_D0002', 'S1-02__D0002', '여성 임직원 비율', 'S1-02', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', '여성 임직원 수 / 전체 임직원 수 * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S1-02__D0002'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S1_02_D0003', 'S1-02__D0003', '정규직 비율', 'S1-02', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S1-02__Q0001;S1-02__Q0003;S1-02__Q0005;S1-02__Q0007;S1-02__Q0009;S1-02__Q0011;S1-02__Q0013;S1-02__Q0015;S1-02__Q0017;S1-02__Q0019;S1-02__Q0021;S1-02__Q0023;S1-02__Q0025;S1-02__Q0027;S1-02__Q0029;S1-02__Q0031;S1-02__Q0033;S1-02__Q0035;S1-02__Q0037;S1-02__Q0039;S1-02__Q0041;S1-02__Q0043;S1-02__Q0045;S1-02__Q0047;S1-02__Q0049;S1-02__Q0051;S1-02__Q0053;S1-02__Q0055;S1-02__Q0057;S1-02__Q0059', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', '정규직 임직원 수 / 전체 임직원 수 * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0003'', ''S1-02__Q0005'', ''S1-02__Q0007'', ''S1-02__Q0009'', ''S1-02__Q0011'', ''S1-02__Q0013'', ''S1-02__Q0015'', ''S1-02__Q0017'', ''S1-02__Q0019'', ''S1-02__Q0021'', ''S1-02__Q0023'', ''S1-02__Q0025'', ''S1-02__Q0027'', ''S1-02__Q0029'', ''S1-02__Q0031'', ''S1-02__Q0033'', ''S1-02__Q0035'', ''S1-02__Q0037'', ''S1-02__Q0039'', ''S1-02__Q0041'', ''S1-02__Q0043'', ''S1-02__Q0045'', ''S1-02__Q0047'', ''S1-02__Q0049'', ''S1-02__Q0051'', ''S1-02__Q0053'', ''S1-02__Q0055'', ''S1-02__Q0057'', ''S1-02__Q0059'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S1-02__D0003'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S1_02_D0004', 'S1-02__D0004', '해외 임직원 비율', 'S1-02', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'EU+US 임직원 수 / 전체 임직원 수 * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S1-02__D0004'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S3_02_D0002', 'S3-02__D0002', '핵심직무 교육 달성률', 'S3-02', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S3-02__Q0003', 'S3-02__Q0002', 'completed / target * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__Q0003'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__Q0002'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S3-02__D0002'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S6_04_D0001', 'S6-04__D0001', '공급업체 감사 수행률', 'S6-04', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S6-04__Q0002', 'S6-04__Q0001', 'audit completed / audit target * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S6-04__Q0002'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S6-04__Q0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S6-04__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_S6_05_D0001', 'S6-05__D0001', '공급망 CAP 완료율', 'S6-05', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S6-05__Q0002', 'S6-05__Q0001', 'CAP completed / CAP total * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S6-05__Q0002'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S6-05__Q0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S6-05__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 25),
('CR_AP_E_06_D0001', 'AP-E-06__D0001', '친환경 제품 매출 비중', 'AP-E-06', 'ENTITY_RATIO', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'AP-E-06__Q0001', 'AP-E-06__R0001', 'low carbon product revenue / total revenue * 100', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''AP-E-06__Q0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''AP-E-06__R0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''AP-E-06__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 26),
('CR_S3_02_D0001', 'S3-02__D0001', '1인당 교육시간', 'S3-02', 'ENTITY_DIVIDE', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', NULL, 'S3-02__Q0001', 'S3-02__R0001', 'total training hours / employee count', 'WITH numerator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__Q0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
),
denominator AS (
  SELECT company_id, reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__R0001'')
    AND approval_status = ''approved''
  GROUP BY company_id, reporting_year
)
SELECT
  n.company_id,
  n.reporting_year,
  ''S3-02__D0001'' AS atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value), 2)
  END AS value_numeric,
  ''시간/명'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM numerator n
JOIN denominator d
  ON n.company_id = d.company_id
 AND n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '시간/명', 26),
('CR_E1_06_D0002', 'E1-06__D0002', '전년 대비 온실가스 감축량', 'E1-06', 'ENTITY_YOY_DIFF', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06__D0001', NULL, NULL, 'prior year total - current year total', 'WITH current_year AS (
  SELECT company_id, reporting_year, value_numeric AS current_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id = ''E1-06__D0001''
    AND approval_status = ''approved''
),
previous_year AS (
  SELECT company_id, reporting_year + 1 AS reporting_year, value_numeric AS previous_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year - 1
    AND atomic_metric_id = ''E1-06__D0001''
    AND approval_status = ''approved''
)
SELECT
  c.company_id,
  c.reporting_year,
  ''E1-06__D0002'' AS atomic_metric_id,
  p.previous_value - c.current_value AS value_numeric,
  ''tCO2eq'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM current_year c
JOIN previous_year p
  ON c.company_id = p.company_id
 AND c.reporting_year = p.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', 'tCO2eq', 30),
('CR_E1_06_D0003', 'E1-06__D0003', '전년 대비 온실가스 감축률', 'E1-06', 'ENTITY_YOY_RATE', 'ENTITY', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06__D0002;E1-06__D0001', NULL, NULL, 'reduction amount / prior year total * 100', 'WITH reduction AS (
  SELECT company_id, reporting_year, value_numeric AS reduction_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year
    AND atomic_metric_id = ''E1-06__D0002''
    AND approval_status = ''approved''
),
prior_total AS (
  SELECT company_id, reporting_year + 1 AS reporting_year, value_numeric AS prior_total_value
  FROM esg_kpi_fact
  WHERE company_id = :company_id
    AND reporting_year = :reporting_year - 1
    AND atomic_metric_id = ''E1-06__D0001''
    AND approval_status = ''approved''
)
SELECT
  r.company_id,
  r.reporting_year,
  ''E1-06__D0003'' AS atomic_metric_id,
  CASE
    WHEN p.prior_total_value = 0 THEN NULL
    ELSE ROUND((r.reduction_value / p.prior_total_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''calculated'' AS value_source_type,
  ''approved'' AS approval_status
FROM reduction r
JOIN prior_total p
  ON r.company_id = p.company_id
 AND r.reporting_year = p.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_kpi_fact', '%', 31),
('CR_AP_E_06_G0001', 'AP-E-06__G0001', '연결 친환경 제품 매출액', 'AP-E-06', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-E-06__Q0001', NULL, NULL, 'SUM(entity low carbon product revenue)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-E-06'' AS group_metric_id,
  ''AP-E-06__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''KRW'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-E-06__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'KRW', 50),
('CR_AP_E_06_G0004', 'AP-E-06__G0004', '연결 회피 배출량', 'AP-E-06', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-E-06__Q0002', NULL, NULL, 'SUM(entity avoided emissions)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-E-06'' AS group_metric_id,
  ''AP-E-06__G0004'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-E-06__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 50),
('CR_AP_E_06_G0005', 'AP-E-06__G0005', '연결 사회적 비용 절감 효과', 'AP-E-06', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-E-06__Q0003', NULL, NULL, 'SUM(entity social cost savings)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-E-06'' AS group_metric_id,
  ''AP-E-06__G0005'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''KRW'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-E-06__Q0003'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'KRW', 50),
('CR_AP_S_01_G0001', 'AP-S-01__G0001', '연결 필드액션 건수', 'AP-S-01', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-S-01__Q0001', NULL, NULL, 'SUM(entity field action count)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-S-01'' AS group_metric_id,
  ''AP-S-01__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-S-01__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_AP_S_01_G0002', 'AP-S-01__G0002', '연결 리콜 건수', 'AP-S-01', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-S-01__Q0002', NULL, NULL, 'SUM(entity recall count)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-S-01'' AS group_metric_id,
  ''AP-S-01__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-S-01__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_AP_S_01_G0003', 'AP-S-01__G0003', '연결 제품안전 CAP 전체 건수', 'AP-S-01', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-S-01__Q0003', NULL, NULL, 'SUM(entity CAP total)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-S-01'' AS group_metric_id,
  ''AP-S-01__G0003'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-S-01__Q0003'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_AP_S_01_G0004', 'AP-S-01__G0004', '연결 제품안전 CAP 완료 건수', 'AP-S-01', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'AP-S-01__Q0004', NULL, NULL, 'SUM(entity CAP completed)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-S-01'' AS group_metric_id,
  ''AP-S-01__G0004'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''AP-S-01__Q0004'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_E1_05_G0001', 'E1-05__G0001', '기준연도 연결 Scope 1 배출량', 'E1-05', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-05__Q0001', NULL, NULL, 'SUM(entity baseline Scope 1)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-05'' AS group_metric_id,
  ''E1-05__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-05__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 50),
('CR_E1_05_G0002', 'E1-05__G0002', '기준연도 연결 Scope 2 배출량', 'E1-05', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-05__Q0002', NULL, NULL, 'SUM(entity baseline Scope 2)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-05'' AS group_metric_id,
  ''E1-05__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-05__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 50),
('CR_E1_06_G0001', 'E1-06__G0001', '연결 Scope 1 배출량', 'E1-06', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-06__Q0001', NULL, NULL, 'SUM(entity Scope 1 across A/B/C/D)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-06'' AS group_metric_id,
  ''E1-06__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-06__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 50),
('CR_E1_06_G0002', 'E1-06__G0002', '연결 Scope 2 배출량', 'E1-06', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-06__Q0002', NULL, NULL, 'SUM(entity Scope 2 across A/B/C/D)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-06'' AS group_metric_id,
  ''E1-06__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-06__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 50),
('CR_E1_07_G0001', 'E1-07__G0001', '연결 총 전력 사용량', 'E1-07', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-07__Q0001', NULL, NULL, 'SUM(entity total electricity)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-07'' AS group_metric_id,
  ''E1-07__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''MWh'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-07__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'MWh', 50),
('CR_E1_07_G0002', 'E1-07__G0002', '연결 재생에너지 사용량', 'E1-07', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-07__Q0002', NULL, NULL, 'SUM(entity renewable electricity)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-07'' AS group_metric_id,
  ''E1-07__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''MWh'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''E1-07__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'MWh', 50),
('CR_G0_02_G0001', 'G0-02__G0001', '연결 매출액', 'G0-02', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'G0-02__Q0001', NULL, NULL, 'SUM(entity revenue)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''G0-02'' AS group_metric_id,
  ''G0-02__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''KRW'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''G0-02__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'KRW', 50),
('CR_G0_02_G0002', 'G0-02__G0002', '연결 영업이익', 'G0-02', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'G0-02__Q0002', NULL, NULL, 'SUM(entity operating profit)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''G0-02'' AS group_metric_id,
  ''G0-02__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''KRW'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''G0-02__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', 'KRW', 50),
('CR_G0_03_G0001', 'G0-03__G0001', '연결 전체 사업장 수', 'G0-03', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'G0-03__Q0001', NULL, NULL, 'SUM(entity total site count)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''G0-03'' AS group_metric_id,
  ''G0-03__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''개'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''G0-03__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '개', 50),
('CR_S1_02_G0001', 'S1-02__G0001', '연결 전체 임직원 수', 'S1-02', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', NULL, NULL, 'SUM(entity total employees)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S1-02'' AS group_metric_id,
  ''S1-02__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''명'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '명', 50),
('CR_S3_02_G0001', 'S3-02__G0001', '연결 총 교육시간', 'S3-02', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S3-02__Q0001', NULL, NULL, 'SUM(entity total training hours)', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S3-02'' AS group_metric_id,
  ''S3-02__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''시간'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S3-02__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '시간', 50),
('CR_S6_04_G0001', 'S6-04__G0001', '연결 감사 대상 공급업체 수', 'S6-04', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S6-04__Q0001', NULL, NULL, 'SUM', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-04'' AS group_metric_id,
  ''S6-04__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''개사'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S6-04__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '개사', 50),
('CR_S6_04_G0002', 'S6-04__G0002', '연결 감사 완료 공급업체 수', 'S6-04', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S6-04__Q0002', NULL, NULL, 'SUM', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-04'' AS group_metric_id,
  ''S6-04__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''개사'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S6-04__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '개사', 50),
('CR_S6_04_G0004', 'S6-04__G0004', '연결 고위험 공급업체 수', 'S6-04', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S6-04__Q0003', NULL, NULL, 'SUM', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-04'' AS group_metric_id,
  ''S6-04__G0004'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''개사'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S6-04__Q0003'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '개사', 50),
('CR_S6_05_G0001', 'S6-05__G0001', '연결 공급망 CAP 전체 건수', 'S6-05', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S6-05__Q0001', NULL, NULL, 'SUM', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-05'' AS group_metric_id,
  ''S6-05__G0001'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S6-05__Q0001'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_S6_05_G0002', 'S6-05__G0002', '연결 공급망 CAP 완료 건수', 'S6-05', 'ROLLUP_SUM', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S6-05__Q0002', NULL, NULL, 'SUM', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-05'' AS group_metric_id,
  ''S6-05__G0002'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''건'' AS unit,
  jsonb_object_agg(company_id, value_numeric ORDER BY company_id) AS source_company_values_json,
  ''SUM'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_kpi_fact
WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
  AND reporting_year = :reporting_year
  AND atomic_metric_id IN (''S6-05__Q0002'')
  AND approval_status = ''approved''
GROUP BY reporting_year;', 'NOT_APPLICABLE', 'ROUND_2DP', 'esg_group_rollup_result', '건', 50),
('CR_AP_E_06_G0002', 'AP-E-06__G0002', '연결 전체 매출액 참조', 'AP-E-06', 'ROLLUP_REFERENCE_COPY', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'G0-02__G0001', NULL, NULL, 'G0-02__G0001', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-E-06'' AS group_metric_id,
  ''AP-E-06__G0002'' AS group_atomic_metric_id,
  value_numeric,
  ''KRW'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''REFERENCE_COPY'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_group_rollup_result
WHERE parent_company_id = ''A_GROUP''
  AND parent_company_scope_type = ''CONSOLIDATED''
  AND reporting_year = :reporting_year
  AND group_atomic_metric_id = ''G0-02__G0001''
  AND rollup_status = ''approved'';', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', 'KRW', 60),
('CR_E1_05_G0003', 'E1-05__G0003', '기준연도 연결 Scope 1·2 총배출량', 'E1-05', 'ROLLUP_ADD', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-05__G0001;E1-05__G0002', NULL, NULL, 'E1-05__G0001 + E1-05__G0002', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-05'' AS group_metric_id,
  ''E1-05__G0003'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RECALCULATE'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_group_rollup_result
WHERE parent_company_id = ''A_GROUP''
  AND parent_company_scope_type = ''CONSOLIDATED''
  AND reporting_year = :reporting_year
  AND group_atomic_metric_id IN (''E1-05__G0001'', ''E1-05__G0002'')
  AND rollup_status = ''approved''
GROUP BY reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 60),
('CR_E1_06_G0003', 'E1-06__G0003', '연결 Scope 1·2 총배출량', 'E1-06', 'ROLLUP_ADD', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-06__G0001;E1-06__G0002', NULL, NULL, 'G0001 + G0002', 'SELECT
  :rollup_batch_id AS rollup_batch_id,
  :reporting_year AS reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-06'' AS group_metric_id,
  ''E1-06__G0003'' AS group_atomic_metric_id,
  SUM(value_numeric) AS value_numeric,
  ''tCO2eq'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RECALCULATE'' AS rollup_method,
  ''approved'' AS rollup_status
FROM esg_group_rollup_result
WHERE parent_company_id = ''A_GROUP''
  AND parent_company_scope_type = ''CONSOLIDATED''
  AND reporting_year = :reporting_year
  AND group_atomic_metric_id IN (''E1-06__G0001'', ''E1-06__G0002'')
  AND rollup_status = ''approved''
GROUP BY reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 60),
('CR_AP_E_06_G0003', 'AP-E-06__G0003', '연결 친환경 제품 매출 비중', 'AP-E-06', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'AP-E-06__G0001', 'AP-E-06__G0002', 'G0001 / G0002 * 100', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''AP-E-06__G0001''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''AP-E-06__G0002''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-E-06'' AS group_metric_id,
  ''AP-E-06__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_AP_S_01_G0005', 'AP-S-01__G0005', '연결 제품안전 CAP 완료율', 'AP-S-01', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'AP-S-01__G0004', 'AP-S-01__G0003', 'G0004 / G0003 * 100', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''AP-S-01__G0004''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''AP-S-01__G0003''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''AP-S-01'' AS group_metric_id,
  ''AP-S-01__G0005'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_E1_07_G0003', 'E1-07__G0003', '연결 재생에너지 전환율', 'E1-07', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'E1-07__G0002', 'E1-07__G0001', 'G0002 / G0001 * 100', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''E1-07__G0002''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''E1-07__G0001''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-07'' AS group_metric_id,
  ''E1-07__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S1_02_G0002', 'S1-02__G0002', '연결 여성 임직원 비율', 'S1-02', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060;S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'SUM(female employees) / SUM(total employees) * 100', 'WITH numerator AS (
  SELECT reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
),
denominator AS (
  SELECT reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S1-02'' AS group_metric_id,
  ''S1-02__G0002'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  jsonb_build_object(''female_employee_count'', n.numerator_value, ''denominator_total'', d.denominator_value) AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S1_02_G0003', 'S1-02__G0003', '연결 정규직 비율', 'S1-02', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S1-02__Q0001;S1-02__Q0003;S1-02__Q0005;S1-02__Q0007;S1-02__Q0009;S1-02__Q0011;S1-02__Q0013;S1-02__Q0015;S1-02__Q0017;S1-02__Q0019;S1-02__Q0021;S1-02__Q0023;S1-02__Q0025;S1-02__Q0027;S1-02__Q0029;S1-02__Q0031;S1-02__Q0033;S1-02__Q0035;S1-02__Q0037;S1-02__Q0039;S1-02__Q0041;S1-02__Q0043;S1-02__Q0045;S1-02__Q0047;S1-02__Q0049;S1-02__Q0051;S1-02__Q0053;S1-02__Q0055;S1-02__Q0057;S1-02__Q0059', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'SUM(regular employees) / SUM(total employees) * 100', 'WITH numerator AS (
  SELECT reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0003'', ''S1-02__Q0005'', ''S1-02__Q0007'', ''S1-02__Q0009'', ''S1-02__Q0011'', ''S1-02__Q0013'', ''S1-02__Q0015'', ''S1-02__Q0017'', ''S1-02__Q0019'', ''S1-02__Q0021'', ''S1-02__Q0023'', ''S1-02__Q0025'', ''S1-02__Q0027'', ''S1-02__Q0029'', ''S1-02__Q0031'', ''S1-02__Q0033'', ''S1-02__Q0035'', ''S1-02__Q0037'', ''S1-02__Q0039'', ''S1-02__Q0041'', ''S1-02__Q0043'', ''S1-02__Q0045'', ''S1-02__Q0047'', ''S1-02__Q0049'', ''S1-02__Q0051'', ''S1-02__Q0053'', ''S1-02__Q0055'', ''S1-02__Q0057'', ''S1-02__Q0059'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
),
denominator AS (
  SELECT reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S1-02'' AS group_metric_id,
  ''S1-02__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  jsonb_build_object(''regular_employee_count'', n.numerator_value, ''denominator_total'', d.denominator_value) AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S1_02_G0004', 'S1-02__G0004', '연결 해외 임직원 비율', 'S1-02', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'S1-02__Q0001;S1-02__Q0002;S1-02__Q0003;S1-02__Q0004;S1-02__Q0005;S1-02__Q0006;S1-02__Q0007;S1-02__Q0008;S1-02__Q0009;S1-02__Q0010;S1-02__Q0011;S1-02__Q0012;S1-02__Q0013;S1-02__Q0014;S1-02__Q0015;S1-02__Q0016;S1-02__Q0017;S1-02__Q0018;S1-02__Q0019;S1-02__Q0020;S1-02__Q0021;S1-02__Q0022;S1-02__Q0023;S1-02__Q0024;S1-02__Q0025;S1-02__Q0026;S1-02__Q0027;S1-02__Q0028;S1-02__Q0029;S1-02__Q0030;S1-02__Q0031;S1-02__Q0032;S1-02__Q0033;S1-02__Q0034;S1-02__Q0035;S1-02__Q0036;S1-02__Q0037;S1-02__Q0038;S1-02__Q0039;S1-02__Q0040;S1-02__Q0041;S1-02__Q0042;S1-02__Q0043;S1-02__Q0044;S1-02__Q0045;S1-02__Q0046;S1-02__Q0047;S1-02__Q0048;S1-02__Q0049;S1-02__Q0050;S1-02__Q0051;S1-02__Q0052;S1-02__Q0053;S1-02__Q0054;S1-02__Q0055;S1-02__Q0056;S1-02__Q0057;S1-02__Q0058;S1-02__Q0059;S1-02__Q0060', 'SUM(EU/US employees) / SUM(total employees) * 100', 'WITH numerator AS (
  SELECT reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
),
denominator AS (
  SELECT reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S1-02__Q0001'', ''S1-02__Q0002'', ''S1-02__Q0003'', ''S1-02__Q0004'', ''S1-02__Q0005'', ''S1-02__Q0006'', ''S1-02__Q0007'', ''S1-02__Q0008'', ''S1-02__Q0009'', ''S1-02__Q0010'', ''S1-02__Q0011'', ''S1-02__Q0012'', ''S1-02__Q0013'', ''S1-02__Q0014'', ''S1-02__Q0015'', ''S1-02__Q0016'', ''S1-02__Q0017'', ''S1-02__Q0018'', ''S1-02__Q0019'', ''S1-02__Q0020'', ''S1-02__Q0021'', ''S1-02__Q0022'', ''S1-02__Q0023'', ''S1-02__Q0024'', ''S1-02__Q0025'', ''S1-02__Q0026'', ''S1-02__Q0027'', ''S1-02__Q0028'', ''S1-02__Q0029'', ''S1-02__Q0030'', ''S1-02__Q0031'', ''S1-02__Q0032'', ''S1-02__Q0033'', ''S1-02__Q0034'', ''S1-02__Q0035'', ''S1-02__Q0036'', ''S1-02__Q0037'', ''S1-02__Q0038'', ''S1-02__Q0039'', ''S1-02__Q0040'', ''S1-02__Q0041'', ''S1-02__Q0042'', ''S1-02__Q0043'', ''S1-02__Q0044'', ''S1-02__Q0045'', ''S1-02__Q0046'', ''S1-02__Q0047'', ''S1-02__Q0048'', ''S1-02__Q0049'', ''S1-02__Q0050'', ''S1-02__Q0051'', ''S1-02__Q0052'', ''S1-02__Q0053'', ''S1-02__Q0054'', ''S1-02__Q0055'', ''S1-02__Q0056'', ''S1-02__Q0057'', ''S1-02__Q0058'', ''S1-02__Q0059'', ''S1-02__Q0060'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S1-02'' AS group_metric_id,
  ''S1-02__G0004'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  jsonb_build_object(''overseas_employee_count'', n.numerator_value, ''denominator_total'', d.denominator_value) AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S3_02_G0002', 'S3-02__G0002', '연결 1인당 교육시간', 'S3-02', 'ROLLUP_DIVIDE', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S3-02__G0001', 'S1-02__G0001', 'SUM(training hours) / connected employee count', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S3-02__G0001''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S1-02__G0001''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S3-02'' AS group_metric_id,
  ''S3-02__G0002'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) , 2)
  END AS value_numeric,
  ''시간/명'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''DIVIDE_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '시간/명', 61),
('CR_S3_02_G0003', 'S3-02__G0003', '연결 핵심직무 교육 달성률', 'S3-02', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S3-02__Q0003', 'S3-02__Q0002', 'SUM(completed) / SUM(target) * 100', 'WITH numerator AS (
  SELECT reporting_year, SUM(value_numeric) AS numerator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__Q0003'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
),
denominator AS (
  SELECT reporting_year, SUM(value_numeric) AS denominator_value
  FROM esg_kpi_fact
  WHERE company_id IN (''A_GROUP'', ''B_SUB_KR'', ''C_SUB_EU'', ''D_SUB_US'')
    AND reporting_year = :reporting_year
    AND atomic_metric_id IN (''S3-02__Q0002'')
    AND approval_status = ''approved''
  GROUP BY reporting_year
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S3-02'' AS group_metric_id,
  ''S3-02__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  jsonb_build_object(''core_training_completed'', n.numerator_value, ''denominator_total'', d.denominator_value) AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S6_04_G0003', 'S6-04__G0003', '연결 공급업체 감사 수행률', 'S6-04', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S6-04__G0002', 'S6-04__G0001', 'G0002 / G0001 * 100', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S6-04__G0002''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S6-04__G0001''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-04'' AS group_metric_id,
  ''S6-04__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_S6_05_G0003', 'S6-05__G0003', '연결 공급망 CAP 완료율', 'S6-05', 'ROLLUP_RATIO_RECALC', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', NULL, 'S6-05__G0002', 'S6-05__G0001', 'G0002 / G0001 * 100', 'WITH numerator AS (
  SELECT reporting_year, value_numeric AS numerator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S6-05__G0002''
    AND rollup_status = ''approved''
),
denominator AS (
  SELECT reporting_year, value_numeric AS denominator_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''S6-05__G0001''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  n.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''S6-05'' AS group_metric_id,
  ''S6-05__G0003'' AS group_atomic_metric_id,
  CASE
    WHEN d.denominator_value = 0 THEN NULL
    ELSE ROUND((n.numerator_value / d.denominator_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''RATIO_RECALC'' AS rollup_method,
  ''approved'' AS rollup_status
FROM numerator n
JOIN denominator d
  ON n.reporting_year = d.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 61),
('CR_E1_06_G0004', 'E1-06__G0004', '연결 전년 대비 온실가스 감축량', 'E1-06', 'ROLLUP_YOY_DIFF', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-06__G0003', NULL, NULL, 'prior year consolidated total - current year consolidated total', 'WITH current_year AS (
  SELECT reporting_year, value_numeric AS current_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''E1-06__G0003''
    AND rollup_status = ''approved''
),
previous_year AS (
  SELECT reporting_year + 1 AS reporting_year, value_numeric AS previous_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year - 1
    AND group_atomic_metric_id = ''E1-06__G0003''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  c.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-06'' AS group_metric_id,
  ''E1-06__G0004'' AS group_atomic_metric_id,
  p.previous_value - c.current_value AS value_numeric,
  ''tCO2eq'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''YOY_DIFF'' AS rollup_method,
  ''approved'' AS rollup_status
FROM current_year c
JOIN previous_year p
  ON c.reporting_year = p.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', 'tCO2eq', 70),
('CR_E1_06_G0005', 'E1-06__G0005', '연결 전년 대비 온실가스 감축률', 'E1-06', 'ROLLUP_YOY_RATE', 'CONSOLIDATED', 'A_GROUP_CONSOLIDATED', 'E1-06__G0004;E1-06__G0003', NULL, NULL, 'G0004 / prior year G0003 * 100', 'WITH reduction AS (
  SELECT reporting_year, value_numeric AS reduction_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year
    AND group_atomic_metric_id = ''E1-06__G0004''
    AND rollup_status = ''approved''
),
prior_total AS (
  SELECT reporting_year + 1 AS reporting_year, value_numeric AS prior_total_value
  FROM esg_group_rollup_result
  WHERE parent_company_id = ''A_GROUP''
    AND parent_company_scope_type = ''CONSOLIDATED''
    AND reporting_year = :reporting_year - 1
    AND group_atomic_metric_id = ''E1-06__G0003''
    AND rollup_status = ''approved''
)
SELECT
  :rollup_batch_id AS rollup_batch_id,
  r.reporting_year,
  ''A_GROUP'' AS parent_company_id,
  ''CONSOLIDATED'' AS parent_company_scope_type,
  ''A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US'' AS included_company_ids,
  ''E1-06'' AS group_metric_id,
  ''E1-06__G0005'' AS group_atomic_metric_id,
  CASE
    WHEN p.prior_total_value = 0 THEN NULL
    ELSE ROUND((r.reduction_value / p.prior_total_value) * 100, 2)
  END AS value_numeric,
  ''%'' AS unit,
  ''{}''::jsonb AS source_company_values_json,
  ''YOY_RATE'' AS rollup_method,
  ''approved'' AS rollup_status
FROM reduction r
JOIN prior_total p
  ON r.reporting_year = p.reporting_year;', 'RETURN_NULL_AND_FLAG', 'ROUND_2DP', 'esg_group_rollup_result', '%', 71)
ON DUPLICATE KEY UPDATE
    target_atomic_metric_id=VALUES(target_atomic_metric_id),
    target_atomic_name_kr=VALUES(target_atomic_name_kr),
    metric_id=VALUES(metric_id),
    formula_type=VALUES(formula_type),
    execution_scope=VALUES(execution_scope),
    applicable_company_scope=VALUES(applicable_company_scope),
    source_atomic_metric_ids=VALUES(source_atomic_metric_ids),
    numerator_atomic_metric_ids=VALUES(numerator_atomic_metric_ids),
    denominator_atomic_metric_ids=VALUES(denominator_atomic_metric_ids),
    calculation_formula_label=VALUES(calculation_formula_label),
    sql_template=VALUES(sql_template),
    zero_division_policy=VALUES(zero_division_policy),
    rounding_policy=VALUES(rounding_policy),
    result_table=VALUES(result_table),
    output_unit=VALUES(output_unit),
    execution_order=VALUES(execution_order);

INSERT INTO ESG_CALCULATION_RULE_SOURCE (
    calculation_rule_code, target_atomic_metric_id, source_atomic_metric_id, source_role, source_scope, source_metric_id
) VALUES
('CR_AP_E_06_D0001', 'AP-E-06__D0001', 'AP-E-06__R0001', 'denominator', 'ENTITY', 'AP-E-06'),
('CR_AP_E_06_D0001', 'AP-E-06__D0001', 'AP-E-06__Q0001', 'numerator', 'ENTITY', 'AP-E-06'),
('CR_AP_E_06_G0001', 'AP-E-06__G0001', 'AP-E-06__Q0001', 'source', 'CONSOLIDATED', 'AP-E-06'),
('CR_AP_E_06_G0002', 'AP-E-06__G0002', 'G0-02__G0001', 'source', 'CONSOLIDATED', 'G0-02'),
('CR_AP_E_06_G0003', 'AP-E-06__G0003', 'AP-E-06__G0002', 'denominator', 'CONSOLIDATED', 'AP-E-06'),
('CR_AP_E_06_G0003', 'AP-E-06__G0003', 'AP-E-06__G0001', 'numerator', 'CONSOLIDATED', 'AP-E-06'),
('CR_AP_E_06_G0004', 'AP-E-06__G0004', 'AP-E-06__Q0002', 'source', 'CONSOLIDATED', 'AP-E-06'),
('CR_AP_E_06_G0005', 'AP-E-06__G0005', 'AP-E-06__Q0003', 'source', 'CONSOLIDATED', 'AP-E-06'),
('CR_AP_E_06_R0001', 'AP-E-06__R0001', 'G0-02__Q0001', 'source', 'ENTITY', 'G0-02'),
('CR_AP_S_01_D0001', 'AP-S-01__D0001', 'AP-S-01__Q0003', 'denominator', 'ENTITY', 'AP-S-01'),
('CR_AP_S_01_D0001', 'AP-S-01__D0001', 'AP-S-01__Q0004', 'numerator', 'ENTITY', 'AP-S-01'),
('CR_AP_S_01_G0001', 'AP-S-01__G0001', 'AP-S-01__Q0001', 'source', 'CONSOLIDATED', 'AP-S-01'),
('CR_AP_S_01_G0002', 'AP-S-01__G0002', 'AP-S-01__Q0002', 'source', 'CONSOLIDATED', 'AP-S-01'),
('CR_AP_S_01_G0003', 'AP-S-01__G0003', 'AP-S-01__Q0003', 'source', 'CONSOLIDATED', 'AP-S-01'),
('CR_AP_S_01_G0004', 'AP-S-01__G0004', 'AP-S-01__Q0004', 'source', 'CONSOLIDATED', 'AP-S-01'),
('CR_AP_S_01_G0005', 'AP-S-01__G0005', 'AP-S-01__G0003', 'denominator', 'CONSOLIDATED', 'AP-S-01'),
('CR_AP_S_01_G0005', 'AP-S-01__G0005', 'AP-S-01__G0004', 'numerator', 'CONSOLIDATED', 'AP-S-01'),
('CR_E1_05_G0001', 'E1-05__G0001', 'E1-05__Q0001', 'source', 'CONSOLIDATED', 'E1-05'),
('CR_E1_05_G0002', 'E1-05__G0002', 'E1-05__Q0002', 'source', 'CONSOLIDATED', 'E1-05'),
('CR_E1_05_G0003', 'E1-05__G0003', 'E1-05__G0001', 'source', 'CONSOLIDATED', 'E1-05'),
('CR_E1_05_G0003', 'E1-05__G0003', 'E1-05__G0002', 'source', 'CONSOLIDATED', 'E1-05'),
('CR_E1_06_D0001', 'E1-06__D0001', 'E1-06__Q0001', 'source', 'ENTITY', 'E1-06'),
('CR_E1_06_D0001', 'E1-06__D0001', 'E1-06__Q0002', 'source', 'ENTITY', 'E1-06'),
('CR_E1_06_D0002', 'E1-06__D0002', 'E1-06__D0001', 'source', 'ENTITY', 'E1-06'),
('CR_E1_06_D0003', 'E1-06__D0003', 'E1-06__D0001', 'source', 'ENTITY', 'E1-06'),
('CR_E1_06_D0003', 'E1-06__D0003', 'E1-06__D0002', 'source', 'ENTITY', 'E1-06'),
('CR_E1_06_G0001', 'E1-06__G0001', 'E1-06__Q0001', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0002', 'E1-06__G0002', 'E1-06__Q0002', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0003', 'E1-06__G0003', 'E1-06__G0001', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0003', 'E1-06__G0003', 'E1-06__G0002', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0004', 'E1-06__G0004', 'E1-06__G0003', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0005', 'E1-06__G0005', 'E1-06__G0003', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_06_G0005', 'E1-06__G0005', 'E1-06__G0004', 'source', 'CONSOLIDATED', 'E1-06'),
('CR_E1_07_D0001', 'E1-07__D0001', 'E1-07__Q0001', 'denominator', 'ENTITY', 'E1-07'),
('CR_E1_07_D0001', 'E1-07__D0001', 'E1-07__Q0002', 'numerator', 'ENTITY', 'E1-07'),
('CR_E1_07_G0001', 'E1-07__G0001', 'E1-07__Q0001', 'source', 'CONSOLIDATED', 'E1-07'),
('CR_E1_07_G0002', 'E1-07__G0002', 'E1-07__Q0002', 'source', 'CONSOLIDATED', 'E1-07'),
('CR_E1_07_G0003', 'E1-07__G0003', 'E1-07__G0001', 'denominator', 'CONSOLIDATED', 'E1-07'),
('CR_E1_07_G0003', 'E1-07__G0003', 'E1-07__G0002', 'numerator', 'CONSOLIDATED', 'E1-07'),
('CR_G0_02_G0001', 'G0-02__G0001', 'G0-02__Q0001', 'source', 'CONSOLIDATED', 'G0-02'),
('CR_G0_02_G0002', 'G0-02__G0002', 'G0-02__Q0002', 'source', 'CONSOLIDATED', 'G0-02'),
('CR_G0_03_G0001', 'G0-03__G0001', 'G0-03__Q0001', 'source', 'CONSOLIDATED', 'G0-03'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0001', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0002', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0003', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0004', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0005', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0006', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0007', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0008', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0009', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0010', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0011', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0012', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0013', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0014', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0015', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0016', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0017', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0018', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0019', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0020', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0021', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0022', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0023', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0024', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0025', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0026', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0027', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0028', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0029', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0030', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0031', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0032', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0033', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0034', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0035', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0036', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0037', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0038', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0039', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0040', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0041', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0042', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0043', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0044', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0045', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0046', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0047', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0048', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0049', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0050', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0051', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0052', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0053', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0054', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0055', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0056', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0057', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0058', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0059', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0001', 'S1-02__D0001', 'S1-02__Q0060', 'source', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0001', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0002', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0003', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0004', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0005', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0006', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0007', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0008', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0009', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0010', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0011', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0012', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0013', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0014', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0015', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0016', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0017', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0018', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0019', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0020', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0021', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0022', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0023', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0024', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0025', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0026', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0027', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0028', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0029', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0030', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0031', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0032', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0033', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0034', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0035', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0036', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0037', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0038', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0039', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0040', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0041', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0042', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0043', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0044', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0045', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0046', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0047', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0048', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0049', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0050', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0051', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0052', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0053', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0054', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0055', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0056', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0057', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0058', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0059', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0060', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0011', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0012', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0013', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0014', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0015', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0016', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0017', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0018', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0019', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0020', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0031', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0032', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0033', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0034', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0035', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0036', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0037', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0038', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0039', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0040', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0051', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0052', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0053', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0054', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0055', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0056', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0057', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0058', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0059', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0002', 'S1-02__D0002', 'S1-02__Q0060', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0001', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0002', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0003', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0004', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0005', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0006', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0007', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0008', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0009', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0010', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0011', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0012', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0013', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0014', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0015', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0016', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0017', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0018', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0019', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0020', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0021', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0022', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0023', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0024', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0025', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0026', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0027', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0028', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0029', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0030', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0031', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0032', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0033', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0034', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0035', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0036', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0037', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0038', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0039', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0040', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0041', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0042', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0043', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0044', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0045', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0046', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0047', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0048', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0049', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0050', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0051', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0052', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0053', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0054', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0055', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0056', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0057', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0058', 'denominator', 'ENTITY', 'S1-02');

INSERT INTO ESG_CALCULATION_RULE_SOURCE (
    calculation_rule_code, target_atomic_metric_id, source_atomic_metric_id, source_role, source_scope, source_metric_id
) VALUES
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0059', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0060', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0001', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0003', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0005', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0007', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0009', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0011', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0013', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0015', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0017', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0019', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0021', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0023', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0025', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0027', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0029', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0031', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0033', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0035', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0037', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0039', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0041', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0043', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0045', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0047', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0049', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0051', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0053', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0055', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0057', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0003', 'S1-02__D0003', 'S1-02__Q0059', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0001', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0002', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0003', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0004', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0005', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0006', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0007', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0008', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0009', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0010', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0011', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0012', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0013', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0014', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0015', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0016', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0017', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0018', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0019', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0020', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0021', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0022', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0023', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0024', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0025', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0026', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0027', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0028', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0029', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0030', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0031', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0032', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0033', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0034', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0035', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0036', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0037', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0038', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0039', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0040', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0041', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0042', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0043', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0044', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0045', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0046', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0047', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0048', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0049', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0050', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0051', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0052', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0053', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0054', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0055', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0056', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0057', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0058', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0059', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0060', 'denominator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0021', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0022', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0023', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0024', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0025', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0026', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0027', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0028', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0029', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0030', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0031', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0032', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0033', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0034', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0035', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0036', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0037', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0038', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0039', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0040', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0041', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0042', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0043', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0044', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0045', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0046', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0047', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0048', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0049', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0050', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0051', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0052', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0053', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0054', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0055', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0056', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0057', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0058', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0059', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_D0004', 'S1-02__D0004', 'S1-02__Q0060', 'numerator', 'ENTITY', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0001', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0002', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0003', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0004', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0005', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0006', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0007', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0008', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0009', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0010', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0011', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0012', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0013', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0014', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0015', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0016', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0017', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0018', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0019', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0020', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0021', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0022', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0023', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0024', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0025', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0026', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0027', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0028', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0029', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0030', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0031', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0032', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0033', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0034', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0035', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0036', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0037', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0038', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0039', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0040', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0041', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0042', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0043', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0044', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0045', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0046', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0047', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0048', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0049', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0050', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0051', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0052', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0053', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0054', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0055', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0056', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0057', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0058', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0059', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0001', 'S1-02__G0001', 'S1-02__Q0060', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0001', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0002', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0003', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0004', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0005', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0006', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0007', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0008', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0009', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0010', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0011', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0012', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0013', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0014', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0015', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0016', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0017', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0018', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0019', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0020', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0021', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0022', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0023', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0024', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0025', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0026', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0027', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0028', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0029', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0030', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0031', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0032', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0033', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0034', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0035', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0036', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0037', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0038', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0039', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0040', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0041', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0042', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0043', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0044', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0045', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0046', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0047', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0048', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0049', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0050', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0051', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0052', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0053', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0054', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0055', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0056', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0057', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0058', 'denominator', 'CONSOLIDATED', 'S1-02');

INSERT INTO ESG_CALCULATION_RULE_SOURCE (
    calculation_rule_code, target_atomic_metric_id, source_atomic_metric_id, source_role, source_scope, source_metric_id
) VALUES
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0059', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0060', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0011', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0012', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0013', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0014', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0015', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0016', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0017', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0018', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0019', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0020', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0031', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0032', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0033', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0034', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0035', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0036', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0037', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0038', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0039', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0040', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0051', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0052', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0053', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0054', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0055', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0056', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0057', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0058', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0059', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0060', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0001', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0002', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0003', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0004', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0005', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0006', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0007', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0008', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0009', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0010', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0011', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0012', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0013', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0014', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0015', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0016', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0017', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0018', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0019', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0020', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0021', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0022', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0023', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0024', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0025', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0026', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0027', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0028', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0029', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0030', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0031', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0032', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0033', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0034', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0035', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0036', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0037', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0038', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0039', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0040', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0041', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0042', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0043', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0044', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0045', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0046', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0047', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0048', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0049', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0050', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0051', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0052', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0053', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0054', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0055', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0056', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0057', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0058', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0059', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0002', 'S1-02__G0002', 'S1-02__Q0060', 'source', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0001', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0002', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0003', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0004', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0005', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0006', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0007', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0008', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0009', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0010', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0011', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0012', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0013', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0014', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0015', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0016', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0017', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0018', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0019', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0020', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0021', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0022', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0023', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0024', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0025', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0026', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0027', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0028', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0029', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0030', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0031', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0032', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0033', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0034', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0035', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0036', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0037', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0038', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0039', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0040', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0041', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0042', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0043', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0044', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0045', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0046', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0047', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0048', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0049', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0050', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0051', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0052', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0053', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0054', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0055', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0056', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0057', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0058', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0059', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0060', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0001', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0003', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0005', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0007', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0009', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0011', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0013', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0015', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0017', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0019', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0021', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0023', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0025', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0027', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0029', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0031', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0033', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0035', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0037', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0039', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0041', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0043', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0045', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0047', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0049', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0051', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0053', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0055', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0057', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0003', 'S1-02__G0003', 'S1-02__Q0059', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0001', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0002', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0003', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0004', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0005', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0006', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0007', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0008', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0009', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0010', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0011', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0012', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0013', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0014', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0015', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0016', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0017', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0018', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0019', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0020', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0021', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0022', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0023', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0024', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0025', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0026', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0027', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0028', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0029', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0030', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0031', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0032', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0033', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0034', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0035', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0036', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0037', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0038', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0039', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0040', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0041', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0042', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0043', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0044', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0045', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0046', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0047', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0048', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0049', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0050', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0051', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0052', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0053', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0054', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0055', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0056', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0057', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0058', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0059', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0060', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0021', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0022', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0023', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0024', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0025', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0026', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0027', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0028', 'numerator', 'CONSOLIDATED', 'S1-02');

INSERT INTO ESG_CALCULATION_RULE_SOURCE (
    calculation_rule_code, target_atomic_metric_id, source_atomic_metric_id, source_role, source_scope, source_metric_id
) VALUES
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0029', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0030', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0031', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0032', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0033', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0034', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0035', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0036', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0037', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0038', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0039', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0040', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0041', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0042', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0043', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0044', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0045', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0046', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0047', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0048', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0049', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0050', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0051', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0052', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0053', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0054', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0055', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0056', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0057', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0058', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0059', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S1_02_G0004', 'S1-02__G0004', 'S1-02__Q0060', 'numerator', 'CONSOLIDATED', 'S1-02'),
('CR_S3_02_D0001', 'S3-02__D0001', 'S3-02__R0001', 'denominator', 'ENTITY', 'S3-02'),
('CR_S3_02_D0001', 'S3-02__D0001', 'S3-02__Q0001', 'numerator', 'ENTITY', 'S3-02'),
('CR_S3_02_D0002', 'S3-02__D0002', 'S3-02__Q0002', 'denominator', 'ENTITY', 'S3-02'),
('CR_S3_02_D0002', 'S3-02__D0002', 'S3-02__Q0003', 'numerator', 'ENTITY', 'S3-02'),
('CR_S3_02_G0001', 'S3-02__G0001', 'S3-02__Q0001', 'source', 'CONSOLIDATED', 'S3-02'),
('CR_S3_02_G0002', 'S3-02__G0002', 'S1-02__G0001', 'denominator', 'CONSOLIDATED', 'S1-02'),
('CR_S3_02_G0002', 'S3-02__G0002', 'S3-02__G0001', 'numerator', 'CONSOLIDATED', 'S3-02'),
('CR_S3_02_G0003', 'S3-02__G0003', 'S3-02__Q0002', 'denominator', 'CONSOLIDATED', 'S3-02'),
('CR_S3_02_G0003', 'S3-02__G0003', 'S3-02__Q0003', 'numerator', 'CONSOLIDATED', 'S3-02'),
('CR_S3_02_R0001', 'S3-02__R0001', 'S1-02__D0001', 'source', 'ENTITY', 'S1-02'),
('CR_S6_04_D0001', 'S6-04__D0001', 'S6-04__Q0001', 'denominator', 'ENTITY', 'S6-04'),
('CR_S6_04_D0001', 'S6-04__D0001', 'S6-04__Q0002', 'numerator', 'ENTITY', 'S6-04'),
('CR_S6_04_G0001', 'S6-04__G0001', 'S6-04__Q0001', 'source', 'CONSOLIDATED', 'S6-04'),
('CR_S6_04_G0002', 'S6-04__G0002', 'S6-04__Q0002', 'source', 'CONSOLIDATED', 'S6-04'),
('CR_S6_04_G0003', 'S6-04__G0003', 'S6-04__G0001', 'denominator', 'CONSOLIDATED', 'S6-04'),
('CR_S6_04_G0003', 'S6-04__G0003', 'S6-04__G0002', 'numerator', 'CONSOLIDATED', 'S6-04'),
('CR_S6_04_G0004', 'S6-04__G0004', 'S6-04__Q0003', 'source', 'CONSOLIDATED', 'S6-04'),
('CR_S6_05_D0001', 'S6-05__D0001', 'S6-05__Q0001', 'denominator', 'ENTITY', 'S6-05'),
('CR_S6_05_D0001', 'S6-05__D0001', 'S6-05__Q0002', 'numerator', 'ENTITY', 'S6-05'),
('CR_S6_05_G0001', 'S6-05__G0001', 'S6-05__Q0001', 'source', 'CONSOLIDATED', 'S6-05'),
('CR_S6_05_G0002', 'S6-05__G0002', 'S6-05__Q0002', 'source', 'CONSOLIDATED', 'S6-05'),
('CR_S6_05_G0003', 'S6-05__G0003', 'S6-05__G0001', 'denominator', 'CONSOLIDATED', 'S6-05'),
('CR_S6_05_G0003', 'S6-05__G0003', 'S6-05__G0002', 'numerator', 'CONSOLIDATED', 'S6-05');


-- ---------------------------------------------------------------------
-- 5. Group rollup staging/result
-- ---------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS TMP_ESG_GROUP_ROLLUP;
CREATE TEMPORARY TABLE TMP_ESG_GROUP_ROLLUP (
    rollup_result_code VARCHAR(120) NOT NULL,
    rollup_batch_code VARCHAR(100) NOT NULL,
    reporting_year INT NOT NULL,
    parent_company_code VARCHAR(50) NOT NULL,
    parent_company_scope_type VARCHAR(30) NOT NULL,
    included_company_codes TEXT NULL,
    group_metric_id VARCHAR(50) NOT NULL,
    group_atomic_metric_id VARCHAR(80) NOT NULL,
    group_atomic_name VARCHAR(300) NULL,
    value_numeric DECIMAL(30,6) NULL,
    value_text LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    source_company_values_json LONGTEXT NULL,
    rollup_method VARCHAR(50) NULL,
    calculation_trace TEXT NULL,
    rollup_requested_by VARCHAR(100) NULL,
    rollup_requested_at DATETIME NULL,
    rollup_status VARCHAR(30) NULL,
    approved_by_user_code VARCHAR(100) NULL,
    approved_at DATETIME NULL,
    PRIMARY KEY (rollup_result_code)
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO TMP_ESG_GROUP_ROLLUP VALUES
('GR_2022_AP-E-06__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0001', '연결 친환경 제품 매출액', 4298000000000, NULL, 'KRW', '{"A_GROUP": 216000000000, "B_SUB_KR": 1968000000000, "C_SUB_EU": 1102000000000, "D_SUB_US": 1012000000000}', 'SUM', 'SUM AP-E-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-E-06__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0002', '연결 전체 매출액 참조', 17800000000000, NULL, 'KRW', '{}', 'RECALCULATE', 'reference G0-02__G0001', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-E-06__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0003', '연결 친환경 제품 매출 비중', 24.15, NULL, '%', '{}', 'RECALCULATE', 'AP-E-06__G0001 / AP-E-06__G0002 * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-E-06__G0004', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0004', '연결 회피 배출량', 1245000, NULL, 'tCO2eq', '{"A_GROUP": 45000, "B_SUB_KR": 520000, "C_SUB_EU": 310000, "D_SUB_US": 370000}', 'SUM', 'SUM AP-E-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-E-06__G0005', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0005', '연결 사회적 비용 절감 효과', 68973000000, NULL, 'KRW', '{"A_GROUP": 2493000000, "B_SUB_KR": 28808000000, "C_SUB_EU": 17174000000, "D_SUB_US": 20498000000}', 'SUM', 'SUM AP-E-06__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-S-01__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0001', '연결 필드액션 건수', 10, NULL, '건', '{"A_GROUP": 1, "B_SUB_KR": 4, "C_SUB_EU": 2, "D_SUB_US": 3}', 'SUM', 'SUM AP-S-01__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-S-01__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0002', '연결 리콜 건수', 3, NULL, '건', '{"A_GROUP": 0, "B_SUB_KR": 1, "C_SUB_EU": 1, "D_SUB_US": 1}', 'SUM', 'SUM AP-S-01__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-S-01__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0003', '연결 제품안전 CAP 전체 건수', 27, NULL, '건', '{"A_GROUP": 3, "B_SUB_KR": 10, "C_SUB_EU": 6, "D_SUB_US": 8}', 'SUM', 'SUM AP-S-01__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-S-01__G0004', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0004', '연결 제품안전 CAP 완료 건수', 19, NULL, '건', '{"A_GROUP": 2, "B_SUB_KR": 7, "C_SUB_EU": 4, "D_SUB_US": 6}', 'SUM', 'SUM AP-S-01__Q0004 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_AP-S-01__G0005', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0005', '연결 제품안전 CAP 완료율', 70.37, NULL, '%', '{}', 'RECALCULATE', 'AP-S-01__G0004 / AP-S-01__G0003 * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-05__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0001', '기준연도 연결 Scope 1 배출량', 77880, NULL, 'tCO2eq', '{"A_GROUP": 10620, "B_SUB_KR": 30680, "C_SUB_EU": 16520, "D_SUB_US": 20060}', 'SUM', 'SUM E1-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-05__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0002', '기준연도 연결 Scope 2 배출량', 53010, NULL, 'tCO2eq', '{"A_GROUP": 7410, "B_SUB_KR": 20520, "C_SUB_EU": 11400, "D_SUB_US": 13680}', 'SUM', 'SUM E1-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-05__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0003', '기준연도 연결 Scope 1·2 총배출량', 130890, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-05__G0001 + E1-05__G0002', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-06__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0001', '연결 Scope 1 배출량', 66000, NULL, 'tCO2eq', '{"A_GROUP": 9000, "B_SUB_KR": 26000, "C_SUB_EU": 14000, "D_SUB_US": 17000}', 'SUM', 'SUM E1-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-06__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0002', '연결 Scope 2 배출량', 46500, NULL, 'tCO2eq', '{"A_GROUP": 6500, "B_SUB_KR": 18000, "C_SUB_EU": 10000, "D_SUB_US": 12000}', 'SUM', 'SUM E1-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-06__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0003', '연결 Scope 1·2 총배출량', 112500, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-06__G0001 + E1-06__G0002', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-06__G0004', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0004', '연결 전년 대비 온실가스 감축량', NULL, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'not applicable for first year', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-06__G0005', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0005', '연결 전년 대비 온실가스 감축률', NULL, NULL, '%', '{}', 'RECALCULATE', 'not applicable for first year', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-07__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0001', '연결 총 전력 사용량', 211000, NULL, 'MWh', '{"A_GROUP": 25000, "B_SUB_KR": 92000, "C_SUB_EU": 42000, "D_SUB_US": 52000}', 'SUM', 'SUM E1-07__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-07__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0002', '연결 재생에너지 사용량', 20030, NULL, 'MWh', '{"A_GROUP": 1750, "B_SUB_KR": 5520, "C_SUB_EU": 7560, "D_SUB_US": 5200}', 'SUM', 'SUM E1-07__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_E1-07__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0003', '연결 재생에너지 전환율', 9.49, NULL, '%', '{}', 'RECALCULATE', 'E1-07__G0002 / E1-07__G0001 * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_G0-02__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0001', '연결 매출액', 17800000000000, NULL, 'KRW', '{"A_GROUP": 1200000000000, "B_SUB_KR": 8200000000000, "C_SUB_EU": 3800000000000, "D_SUB_US": 4600000000000}', 'SUM', 'SUM G0-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_G0-02__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0002', '연결 영업이익', 956600000000, NULL, 'KRW', '{"A_GROUP": 84000000000, "B_SUB_KR": 451000000000, "C_SUB_EU": 182400000000, "D_SUB_US": 239200000000}', 'SUM', 'SUM G0-02__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_G0-03__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-03', 'G0-03__G0001', '연결 전체 사업장 수', 22, NULL, '개', '{"A_GROUP": 3, "B_SUB_KR": 8, "C_SUB_EU": 5, "D_SUB_US": 6}', 'SUM', 'SUM G0-03__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S1-02__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0001', '연결 전체 임직원 수', 8367, NULL, '명', '{}', 'SUM', 'SUM entity employee counts', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S1-02__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0002', '연결 여성 임직원 비율', 38.02, NULL, '%', '{}', 'SUM', 'SUM female employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S1-02__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0003', '연결 정규직 비율', 88.04, NULL, '%', '{}', 'SUM', 'SUM regular employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S1-02__G0004', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0004', '연결 해외 임직원 비율', 44.45, NULL, '%', '{}', 'SUM', 'SUM overseas employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S3-02__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0001', '연결 총 교육시간', 279648, NULL, '시간', '{"A_GROUP": 27552, "B_SUB_KR": 134400, "C_SUB_EU": 53760, "D_SUB_US": 63936}', 'SUM', 'SUM S3-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S3-02__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0002', '연결 1인당 교육시간', 33.42, NULL, '시간/명', '{}', 'SUM', 'S3-02__G0001 / S1-02__G0001', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S3-02__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0003', '연결 핵심직무 교육 달성률', 72.01, NULL, '%', '{}', 'SUM', 'SUM(S3-02__Q0003) / SUM(S3-02__Q0002) * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-04__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0001', '연결 감사 대상 공급업체 수', 580, NULL, '개사', '{"A_GROUP": 60, "B_SUB_KR": 260, "C_SUB_EU": 120, "D_SUB_US": 140}', 'SUM', 'SUM S6-04__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-04__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0002', '연결 감사 완료 공급업체 수', 417, NULL, '개사', '{"A_GROUP": 43, "B_SUB_KR": 187, "C_SUB_EU": 86, "D_SUB_US": 101}', 'SUM', 'SUM S6-04__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-04__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0003', '연결 공급업체 감사 수행률', 71.9, NULL, '%', '{}', 'RECALCULATE', 'S6-04__G0002 / S6-04__G0001 * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-04__G0004', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0004', '연결 고위험 공급업체 수', 64, NULL, '개사', '{"A_GROUP": 7, "B_SUB_KR": 29, "C_SUB_EU": 13, "D_SUB_US": 15}', 'SUM', 'SUM S6-04__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-05__G0001', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0001', '연결 공급망 CAP 전체 건수', 141, NULL, '건', '{"A_GROUP": 15, "B_SUB_KR": 64, "C_SUB_EU": 29, "D_SUB_US": 33}', 'SUM', 'SUM S6-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-05__G0002', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0002', '연결 공급망 CAP 완료 건수', 96, NULL, '건', '{"A_GROUP": 10, "B_SUB_KR": 44, "C_SUB_EU": 20, "D_SUB_US": 22}', 'SUM', 'SUM S6-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2022_S6-05__G0003', 'ROLLUP_2022_A_GROUP_001', 2022, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0003', '연결 공급망 CAP 완료율', 68.09, NULL, '%', '{}', 'RECALCULATE', 'S6-05__G0002 / S6-05__G0001 * 100', 'U_ESG_MANAGER_A', '2023-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2023-02-20 04:00:00'),
('GR_2023_AP-E-06__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0001', '연결 친환경 제품 매출액', 4715765600000, NULL, 'KRW', '{"A_GROUP": 236995200000, "B_SUB_KR": 2159289600000, "C_SUB_EU": 1209114400000, "D_SUB_US": 1110366400000}', 'SUM', 'SUM AP-E-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-E-06__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0002', '연결 전체 매출액 참조', 18779000000000, NULL, 'KRW', '{}', 'RECALCULATE', 'reference G0-02__G0001', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-E-06__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0003', '연결 친환경 제품 매출 비중', 25.11, NULL, '%', '{}', 'RECALCULATE', 'AP-E-06__G0001 / AP-E-06__G0002 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-E-06__G0004', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0004', '연결 회피 배출량', 1332150, NULL, 'tCO2eq', '{"A_GROUP": 48150, "B_SUB_KR": 556400, "C_SUB_EU": 331700, "D_SUB_US": 395900}', 'SUM', 'SUM AP-E-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-E-06__G0005', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0005', '연결 사회적 비용 절감 효과', 73801110000, NULL, 'KRW', '{"A_GROUP": 2667510000, "B_SUB_KR": 30824560000, "C_SUB_EU": 18376180000, "D_SUB_US": 21932860000}', 'SUM', 'SUM AP-E-06__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-S-01__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0001', '연결 필드액션 건수', 10, NULL, '건', '{"A_GROUP": 1, "B_SUB_KR": 4, "C_SUB_EU": 2, "D_SUB_US": 3}', 'SUM', 'SUM AP-S-01__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-S-01__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0002', '연결 리콜 건수', 3, NULL, '건', '{"A_GROUP": 0, "B_SUB_KR": 1, "C_SUB_EU": 1, "D_SUB_US": 1}', 'SUM', 'SUM AP-S-01__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-S-01__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0003', '연결 제품안전 CAP 전체 건수', 27, NULL, '건', '{"A_GROUP": 3, "B_SUB_KR": 10, "C_SUB_EU": 6, "D_SUB_US": 8}', 'SUM', 'SUM AP-S-01__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-S-01__G0004', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0004', '연결 제품안전 CAP 완료 건수', 21, NULL, '건', '{"A_GROUP": 2, "B_SUB_KR": 8, "C_SUB_EU": 5, "D_SUB_US": 6}', 'SUM', 'SUM AP-S-01__Q0004 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_AP-S-01__G0005', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0005', '연결 제품안전 CAP 완료율', 77.78, NULL, '%', '{}', 'RECALCULATE', 'AP-S-01__G0004 / AP-S-01__G0003 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-05__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0001', '기준연도 연결 Scope 1 배출량', 77880, NULL, 'tCO2eq', '{"A_GROUP": 10620, "B_SUB_KR": 30680, "C_SUB_EU": 16520, "D_SUB_US": 20060}', 'SUM', 'SUM E1-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-05__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0002', '기준연도 연결 Scope 2 배출량', 53010, NULL, 'tCO2eq', '{"A_GROUP": 7410, "B_SUB_KR": 20520, "C_SUB_EU": 11400, "D_SUB_US": 13680}', 'SUM', 'SUM E1-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-05__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0003', '기준연도 연결 Scope 1·2 총배출량', 130890, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-05__G0001 + E1-05__G0002', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-06__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0001', '연결 Scope 1 배출량', 63690, NULL, 'tCO2eq', '{"A_GROUP": 8685, "B_SUB_KR": 25090, "C_SUB_EU": 13510, "D_SUB_US": 16405}', 'SUM', 'SUM E1-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-06__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0002', '연결 Scope 2 배출량', 44408, NULL, 'tCO2eq', '{"A_GROUP": 6208, "B_SUB_KR": 17190, "C_SUB_EU": 9550, "D_SUB_US": 11460}', 'SUM', 'SUM E1-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-06__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0003', '연결 Scope 1·2 총배출량', 108098, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-06__G0001 + E1-06__G0002', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-06__G0004', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0004', '연결 전년 대비 온실가스 감축량', 4402, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'prior year E1-06__G0003 - current year E1-06__G0003', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-06__G0005', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0005', '연결 전년 대비 온실가스 감축률', 3.91, NULL, '%', '{}', 'RECALCULATE', 'E1-06__G0004 / prior year E1-06__G0003 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-07__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0001', '연결 총 전력 사용량', 216275, NULL, 'MWh', '{"A_GROUP": 25625, "B_SUB_KR": 94300, "C_SUB_EU": 43050, "D_SUB_US": 53300}', 'SUM', 'SUM E1-07__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-07__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0002', '연결 재생에너지 사용량', 29806, NULL, 'MWh', '{"A_GROUP": 2562, "B_SUB_KR": 8487, "C_SUB_EU": 10762, "D_SUB_US": 7995}', 'SUM', 'SUM E1-07__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_E1-07__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0003', '연결 재생에너지 전환율', 13.78, NULL, '%', '{}', 'RECALCULATE', 'E1-07__G0002 / E1-07__G0001 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_G0-02__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0001', '연결 매출액', 18779000000000, NULL, 'KRW', '{"A_GROUP": 1266000000000, "B_SUB_KR": 8651000000000, "C_SUB_EU": 4009000000000, "D_SUB_US": 4853000000000}', 'SUM', 'SUM G0-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_G0-02__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0002', '연결 영업이익', 1009213000000, NULL, 'KRW', '{"A_GROUP": 88620000000, "B_SUB_KR": 475805000000, "C_SUB_EU": 192432000000, "D_SUB_US": 252356000000}', 'SUM', 'SUM G0-02__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_G0-03__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-03', 'G0-03__G0001', '연결 전체 사업장 수', 22, NULL, '개', '{"A_GROUP": 3, "B_SUB_KR": 8, "C_SUB_EU": 5, "D_SUB_US": 6}', 'SUM', 'SUM G0-03__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S1-02__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0001', '연결 전체 임직원 수', 8579, NULL, '명', '{}', 'SUM', 'SUM entity employee counts', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S1-02__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0002', '연결 여성 임직원 비율', 37.95, NULL, '%', '{}', 'SUM', 'SUM female employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S1-02__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0003', '연결 정규직 비율', 88.05, NULL, '%', '{}', 'SUM', 'SUM regular employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S1-02__G0004', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0004', '연결 해외 임직원 비율', 44.49, NULL, '%', '{}', 'SUM', 'SUM overseas employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S3-02__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0001', '연결 총 교육시간', 313511, NULL, '시간', '{"A_GROUP": 30888, "B_SUB_KR": 150675, "C_SUB_EU": 60270, "D_SUB_US": 71678}', 'SUM', 'SUM S3-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S3-02__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0002', '연결 1인당 교육시간', 36.54, NULL, '시간/명', '{}', 'SUM', 'S3-02__G0001 / S1-02__G0001', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S3-02__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0003', '연결 핵심직무 교육 달성률', 80.03, NULL, '%', '{}', 'SUM', 'SUM(S3-02__Q0003) / SUM(S3-02__Q0002) * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-04__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0001', '연결 감사 대상 공급업체 수', 627, NULL, '개사', '{"A_GROUP": 65, "B_SUB_KR": 281, "C_SUB_EU": 130, "D_SUB_US": 151}', 'SUM', 'SUM S6-04__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-04__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0002', '연결 감사 완료 공급업체 수', 495, NULL, '개사', '{"A_GROUP": 51, "B_SUB_KR": 222, "C_SUB_EU": 103, "D_SUB_US": 119}', 'SUM', 'SUM S6-04__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-04__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0003', '연결 공급업체 감사 수행률', 78.95, NULL, '%', '{}', 'RECALCULATE', 'S6-04__G0002 / S6-04__G0001 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-04__G0004', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0004', '연결 고위험 공급업체 수', 59, NULL, '개사', '{"A_GROUP": 6, "B_SUB_KR": 27, "C_SUB_EU": 12, "D_SUB_US": 14}', 'SUM', 'SUM S6-04__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-05__G0001', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0001', '연결 공급망 CAP 전체 건수', 129, NULL, '건', '{"A_GROUP": 13, "B_SUB_KR": 59, "C_SUB_EU": 26, "D_SUB_US": 31}', 'SUM', 'SUM S6-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-05__G0002', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0002', '연결 공급망 CAP 완료 건수', 99, NULL, '건', '{"A_GROUP": 10, "B_SUB_KR": 45, "C_SUB_EU": 20, "D_SUB_US": 24}', 'SUM', 'SUM S6-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2023_S6-05__G0003', 'ROLLUP_2023_A_GROUP_001', 2023, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0003', '연결 공급망 CAP 완료율', 76.74, NULL, '%', '{}', 'RECALCULATE', 'S6-05__G0002 / S6-05__G0001 * 100', 'U_ESG_MANAGER_A', '2024-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2024-02-20 04:00:00'),
('GR_2024_AP-E-06__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0001', '연결 친환경 제품 매출액', 5152442400000, NULL, 'KRW', '{"A_GROUP": 258940800000, "B_SUB_KR": 2359238400000, "C_SUB_EU": 1321077600000, "D_SUB_US": 1213185600000}', 'SUM', 'SUM AP-E-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-E-06__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0002', '연결 전체 매출액 참조', 19758000000000, NULL, 'KRW', '{}', 'RECALCULATE', 'reference G0-02__G0001', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-E-06__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0003', '연결 친환경 제품 매출 비중', 26.08, NULL, '%', '{}', 'RECALCULATE', 'AP-E-06__G0001 / AP-E-06__G0002 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-E-06__G0004', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0004', '연결 회피 배출량', 1419300, NULL, 'tCO2eq', '{"A_GROUP": 51300, "B_SUB_KR": 592800, "C_SUB_EU": 353400, "D_SUB_US": 421800}', 'SUM', 'SUM AP-E-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-E-06__G0005', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-E-06', 'AP-E-06__G0005', '연결 사회적 비용 절감 효과', 78629220000, NULL, 'KRW', '{"A_GROUP": 2842020000, "B_SUB_KR": 32841120000, "C_SUB_EU": 19578360000, "D_SUB_US": 23367720000}', 'SUM', 'SUM AP-E-06__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-S-01__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0001', '연결 필드액션 건수', 8, NULL, '건', '{"A_GROUP": 1, "B_SUB_KR": 3, "C_SUB_EU": 2, "D_SUB_US": 2}', 'SUM', 'SUM AP-S-01__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-S-01__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0002', '연결 리콜 건수', 2, NULL, '건', '{"A_GROUP": 0, "B_SUB_KR": 1, "C_SUB_EU": 0, "D_SUB_US": 1}', 'SUM', 'SUM AP-S-01__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-S-01__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0003', '연결 제품안전 CAP 전체 건수', 24, NULL, '건', '{"A_GROUP": 3, "B_SUB_KR": 9, "C_SUB_EU": 5, "D_SUB_US": 7}', 'SUM', 'SUM AP-S-01__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-S-01__G0004', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0004', '연결 제품안전 CAP 완료 건수', 21, NULL, '건', '{"A_GROUP": 3, "B_SUB_KR": 8, "C_SUB_EU": 4, "D_SUB_US": 6}', 'SUM', 'SUM AP-S-01__Q0004 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_AP-S-01__G0005', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'AP-S-01', 'AP-S-01__G0005', '연결 제품안전 CAP 완료율', 87.5, NULL, '%', '{}', 'RECALCULATE', 'AP-S-01__G0004 / AP-S-01__G0003 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-05__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0001', '기준연도 연결 Scope 1 배출량', 77880, NULL, 'tCO2eq', '{"A_GROUP": 10620, "B_SUB_KR": 30680, "C_SUB_EU": 16520, "D_SUB_US": 20060}', 'SUM', 'SUM E1-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-05__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0002', '기준연도 연결 Scope 2 배출량', 53010, NULL, 'tCO2eq', '{"A_GROUP": 7410, "B_SUB_KR": 20520, "C_SUB_EU": 11400, "D_SUB_US": 13680}', 'SUM', 'SUM E1-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-05__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-05', 'E1-05__G0003', '기준연도 연결 Scope 1·2 총배출량', 130890, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-05__G0001 + E1-05__G0002', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-06__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0001', '연결 Scope 1 배출량', 61280, NULL, 'tCO2eq', '{"A_GROUP": 8270, "B_SUB_KR": 24180, "C_SUB_EU": 13020, "D_SUB_US": 15810}', 'SUM', 'SUM E1-06__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-06__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0002', '연결 Scope 2 배출량', 42195, NULL, 'tCO2eq', '{"A_GROUP": 5795, "B_SUB_KR": 16380, "C_SUB_EU": 9100, "D_SUB_US": 10920}', 'SUM', 'SUM E1-06__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-06__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0003', '연결 Scope 1·2 총배출량', 103475, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'E1-06__G0001 + E1-06__G0002', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-06__G0004', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0004', '연결 전년 대비 온실가스 감축량', 4623, NULL, 'tCO2eq', '{}', 'RECALCULATE', 'prior year E1-06__G0003 - current year E1-06__G0003', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-06__G0005', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-06', 'E1-06__G0005', '연결 전년 대비 온실가스 감축률', 4.28, NULL, '%', '{}', 'RECALCULATE', 'E1-06__G0004 / prior year E1-06__G0003 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-07__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0001', '연결 총 전력 사용량', 221550, NULL, 'MWh', '{"A_GROUP": 26250, "B_SUB_KR": 96600, "C_SUB_EU": 44100, "D_SUB_US": 54600}', 'SUM', 'SUM E1-07__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-07__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0002', '연결 재생에너지 사용량', 42273, NULL, 'MWh', '{"A_GROUP": 3675, "B_SUB_KR": 11592, "C_SUB_EU": 14994, "D_SUB_US": 12012}', 'SUM', 'SUM E1-07__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_E1-07__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'E1-07', 'E1-07__G0003', '연결 재생에너지 전환율', 19.08, NULL, '%', '{}', 'RECALCULATE', 'E1-07__G0002 / E1-07__G0001 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_G0-02__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0001', '연결 매출액', 19758000000000, NULL, 'KRW', '{"A_GROUP": 1332000000000, "B_SUB_KR": 9102000000000, "C_SUB_EU": 4218000000000, "D_SUB_US": 5106000000000}', 'SUM', 'SUM G0-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_G0-02__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-02', 'G0-02__G0002', '연결 영업이익', 1061826000000, NULL, 'KRW', '{"A_GROUP": 93240000000, "B_SUB_KR": 500610000000, "C_SUB_EU": 202464000000, "D_SUB_US": 265512000000}', 'SUM', 'SUM G0-02__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_G0-03__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'G0-03', 'G0-03__G0001', '연결 전체 사업장 수', 24, NULL, '개', '{"A_GROUP": 3, "B_SUB_KR": 9, "C_SUB_EU": 6, "D_SUB_US": 6}', 'SUM', 'SUM G0-03__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00');

INSERT INTO TMP_ESG_GROUP_ROLLUP VALUES
('GR_2024_S1-02__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0001', '연결 전체 임직원 수', 8788, NULL, '명', '{}', 'SUM', 'SUM entity employee counts', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S1-02__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0002', '연결 여성 임직원 비율', 38.01, NULL, '%', '{}', 'SUM', 'SUM female employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S1-02__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0003', '연결 정규직 비율', 87.99, NULL, '%', '{}', 'SUM', 'SUM regular employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S1-02__G0004', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S1-02', 'S1-02__G0004', '연결 해외 임직원 비율', 44.48, NULL, '%', '{}', 'SUM', 'SUM overseas employees / SUM total employees * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S3-02__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0001', '연결 총 교육시간', 348686, NULL, '시간', '{"A_GROUP": 34354, "B_SUB_KR": 167580, "C_SUB_EU": 67032, "D_SUB_US": 79720}', 'SUM', 'SUM S3-02__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S3-02__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0002', '연결 1인당 교육시간', 39.68, NULL, '시간/명', '{}', 'SUM', 'S3-02__G0001 / S1-02__G0001', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S3-02__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S3-02', 'S3-02__G0003', '연결 핵심직무 교육 달성률', 88.03, NULL, '%', '{}', 'SUM', 'SUM(S3-02__Q0003) / SUM(S3-02__Q0002) * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-04__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0001', '연결 감사 대상 공급업체 수', 673, NULL, '개사', '{"A_GROUP": 70, "B_SUB_KR": 302, "C_SUB_EU": 139, "D_SUB_US": 162}', 'SUM', 'SUM S6-04__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-04__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0002', '연결 감사 완료 공급업체 수', 579, NULL, '개사', '{"A_GROUP": 60, "B_SUB_KR": 260, "C_SUB_EU": 120, "D_SUB_US": 139}', 'SUM', 'SUM S6-04__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-04__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0003', '연결 공급업체 감사 수행률', 86.03, NULL, '%', '{}', 'RECALCULATE', 'S6-04__G0002 / S6-04__G0001 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-04__G0004', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-04', 'S6-04__G0004', '연결 고위험 공급업체 수', 54, NULL, '개사', '{"A_GROUP": 6, "B_SUB_KR": 24, "C_SUB_EU": 11, "D_SUB_US": 13}', 'SUM', 'SUM S6-04__Q0003 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-05__G0001', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0001', '연결 공급망 CAP 전체 건수', 119, NULL, '건', '{"A_GROUP": 13, "B_SUB_KR": 53, "C_SUB_EU": 24, "D_SUB_US": 29}', 'SUM', 'SUM S6-05__Q0001 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-05__G0002', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0002', '연결 공급망 CAP 완료 건수', 100, NULL, '건', '{"A_GROUP": 11, "B_SUB_KR": 45, "C_SUB_EU": 20, "D_SUB_US": 24}', 'SUM', 'SUM S6-05__Q0002 across A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00'),
('GR_2024_S6-05__G0003', 'ROLLUP_2024_A_GROUP_001', 2024, 'A_GROUP', 'CONSOLIDATED', 'A_GROUP;B_SUB_KR;C_SUB_EU;D_SUB_US', 'S6-05', 'S6-05__G0003', '연결 공급망 CAP 완료율', 84.03, NULL, '%', '{}', 'RECALCULATE', 'S6-05__G0002 / S6-05__G0001 * 100', 'U_ESG_MANAGER_A', '2025-02-20 00:00:00', 'approved', 'U_FINAL_APPROVER_A', '2025-02-20 04:00:00');


INSERT INTO ESG_ROLLUP_BATCH (
    rollup_batch_code, parent_company_id, reporting_year, batch_status, requested_by_user_id, completed_at
)
SELECT DISTINCT
    t.rollup_batch_code,
    p.company_id,
    t.reporting_year,
    'approved',
    @user_id_esg_admin,
    MAX(t.approved_at)
FROM TMP_ESG_GROUP_ROLLUP t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.parent_company_code
GROUP BY t.rollup_batch_code, p.company_id, t.reporting_year
ON DUPLICATE KEY UPDATE
    batch_status=VALUES(batch_status),
    requested_by_user_id=VALUES(requested_by_user_id),
    completed_at=VALUES(completed_at);

INSERT INTO ESG_GROUP_ROLLUP_RESULT (
    esg_rollup_batch_id, rollup_result_code, reporting_year, parent_company_id,
    parent_company_scope_type, included_company_ids, group_metric_id, group_atomic_metric_id,
    group_atomic_name, value_numeric, value_text, unit, source_company_values_json,
    rollup_method, calculation_trace, rollup_status, approved_by_user_id, approved_at
)
SELECT
    b.id,
    t.rollup_result_code,
    t.reporting_year,
    p.company_id,
    t.parent_company_scope_type,
    t.included_company_codes,
    t.group_metric_id,
    t.group_atomic_metric_id,
    t.group_atomic_name,
    t.value_numeric,
    t.value_text,
    t.unit,
    t.source_company_values_json,
    t.rollup_method,
    t.calculation_trace,
    COALESCE(t.rollup_status, 'approved'),
    @user_id_approver,
    t.approved_at
FROM TMP_ESG_GROUP_ROLLUP t
JOIN ESG_COMPANY_PROFILE p ON p.company_code=t.parent_company_code
JOIN ESG_ROLLUP_BATCH b ON b.rollup_batch_code=t.rollup_batch_code
ON DUPLICATE KEY UPDATE
    rollup_result_code=VALUES(rollup_result_code),
    value_numeric=VALUES(value_numeric),
    value_text=VALUES(value_text),
    unit=VALUES(unit),
    source_company_values_json=VALUES(source_company_values_json),
    rollup_method=VALUES(rollup_method),
    calculation_trace=VALUES(calculation_trace),
    rollup_status=VALUES(rollup_status),
    approved_by_user_id=VALUES(approved_by_user_id),
    approved_at=VALUES(approved_at);



SET FOREIGN_KEY_CHECKS = 1;
COMMIT;

SELECT 'CLEAN_SCHEMA_v2 onboarding-only seed completed' AS status;
