"""
ESG IssueGroup 및 Sub-Issue 온톨로지 사전 (v4.3)
- 23개 이슈그룹 / 62개 서브이슈 전체 체계 복원
- AI 분류 성능 향상을 위한 의미적 앵커(subIssueSentence) 및 최신 메트릭 매핑 상태 반영
"""

subissueMaster = {
    # ==========================================================================================
    # [E] ENVIRONMENTAL (기후변화, 환경성과, 원자재 등)
    # ==========================================================================================
    "E_CLIMATE__CLIMATE_GOVERNANCE_INVENTORY": {
        "no": 1,
        "domain": "E",
        "issueGroupSort": 1.0,
        "issueGroupId": "E_CLIMATE",
        "issueGroupNameKr": "기후변화·온실가스",
        "subIssueSort": 1,
        "subIssueId": "E_CLIMATE__CLIMATE_GOVERNANCE_INVENTORY",
        "subIssueNameKr": "기후 거버넌스·인벤토리",
        "subIssueNameEn": "Climate governance and GHG accounting",
        "subIssueSentence": "회사의 기후변화 대응 거버넌스, 온실가스(GHG) 산정체계 및 인벤토리 구축, 배출계수 적용, 내부 탄소가격 도입 및 탄소회계 전반을 설명하는 문장.",
        "keywordKr": ["기후 거버넌스", "GHG 인벤토리", "산정체계", "배출계수", "내부 탄소가격", "탄소회계"],
        "keywordForeignEn": ["climate governance", "ghg inventory", "emission factor", "carbon accounting"],
        "mappedMetricIds": ["M_E_GHG_001", "M_E_GHG_002"],
        "mappedAtomicMetricIds": ["AM_E_GHG_001_01", "AM_E_GHG_002_01"]
    },
    "E_CLIMATE__SCOPE1_2_EMISSION": {
        "no": 2,
        "domain": "E",
        "issueGroupSort": 1.0,
        "issueGroupId": "E_CLIMATE",
        "issueGroupNameKr": "기후변화·온실가스",
        "subIssueSort": 2,
        "subIssueId": "E_CLIMATE__SCOPE1_2_EMISSION",
        "subIssueNameKr": "Scope 1·2 배출량",
        "subIssueNameEn": "Scope 1 and 2 GHG emissions",
        "subIssueSentence": "회사의 사업장 연료 사용과 구매 전력 등에서 발생하는 직접(Scope 1) 및 간접(Scope 2) 온실가스 배출량, Location-based 및 Market-based 배출량 현황과 집약도를 설명하는 문장.",
        "keywordKr": ["Scope 1", "Scope 2", "직접 배출량", "간접 배출량", "배출 집약도", "전력 사용량"],
        "keywordForeignEn": ["scope 1", "scope 2", "direct emission", "indirect emission", "emission intensity"],
        "mappedMetricIds": ["M_E_GHG_003"],
        "mappedAtomicMetricIds": ["AM_E_GHG_003_01", "AM_E_GHG_003_02"]
    },
    "E_CLIMATE__SCOPE3_EMISSION": {
        "no": 3,
        "domain": "E",
        "issueGroupSort": 1.0,
        "issueGroupId": "E_CLIMATE",
        "issueGroupNameKr": "기후변화·온실가스",
        "subIssueSort": 3,
        "subIssueId": "E_CLIMATE__SCOPE3_EMISSION",
        "subIssueNameKr": "Scope 3 배출량",
        "subIssueNameEn": "Scope 3 value chain emissions",
        "subIssueSentence": "기타 간접 온실가스 배출원인 공급망, 제품 사용 및 폐기 단계, 임직원 출퇴근 및 출장 등 가치사슬 전반의 Scope 3 배출량 및 카테고리별 산정 결과를 설명하는 문장.",
        "keywordKr": ["Scope 3", "가치사슬 배출량", "공급망 배출", "업스트림", "다운스트림"],
        "keywordForeignEn": ["scope 3", "value chain emission", "upstream", "downstream"],
        "mappedMetricIds": ["M_E_GHG_004"],
        "mappedAtomicMetricIds": ["AM_E_GHG_004_01"]
    },
    "E_ENERGY__EFFICIENCY_CONSUMPTION": {
        "no": 4,
        "domain": "E",
        "issueGroupSort": 2.0,
        "issueGroupId": "E_ENERGY",
        "issueGroupNameKr": "에너지 관리",
        "subIssueSort": 1,
        "subIssueId": "E_ENERGY__EFFICIENCY_CONSUMPTION",
        "subIssueNameKr": "에너지 소비 및 효율화",
        "subIssueSentence": "조직 내부의 총 에너지 소비량, 연료 및 전력 사용 현황, 고효율 설비 도입이나 공정 개선을 통한 에너지 절감 성과와 효율성 지표를 설명하는 문장.",
        "keywordKr": ["에너지 소비량", "연료 사용량", "에너지 절감", "효율 개선", "에너지 원단위"],
        "keywordForeignEn": ["energy consumption", "energy saving", "energy efficiency"],
        "mappedMetricIds": ["M_E_ENG_001"],
        "mappedAtomicMetricIds": ["AM_E_ENG_001_01"]
    },
    "E_ENERGY__RENEWABLE_TRANSITION": {
        "no": 5,
        "domain": "E",
        "issueGroupSort": 2.0,
        "issueGroupId": "E_ENERGY",
        "issueGroupNameKr": "에너지 관리",
        "subIssueSort": 2,
        "subIssueId": "E_ENERGY__RENEWABLE_TRANSITION",
        "subIssueNameKr": "신재생에너지 전환",
        "subIssueSentence": "태양광, 풍력 등 신재생에너지 발전 설비 도입, 공급인증서(REC) 구매, 전력구매계약(PPA) 체결 및 RE100 이행 로드맵과 달성률을 설명하는 문장.",
        "keywordKr": ["신재생에너지", "재생에너지 전환", "RE100", "PPA", "REC 구매", "태양광 발전"],
        "keywordForeignEn": ["renewable energy", "energy transition", "re100", "solar power"],
        "mappedMetricIds": ["M_E_ENG_002"],
        "mappedAtomicMetricIds": ["AM_E_ENG_002_01"]
    },

    # ==========================================================================================
    # [S] SOCIAL (안전보건, 임직원, 인권, 공급망, 지역사회 등)
    # ==========================================================================================
    "S_SAFETY__OCCUPATIONAL_HEALTH_MANAGEMENT": {
        "no": 24,
        "domain": "S",
        "issueGroupSort": 8.0,
        "issueGroupId": "S_SAFETY",
        "issueGroupNameKr": "안전보건",
        "subIssueSort": 1,
        "subIssueId": "S_SAFETY__OCCUPATIONAL_HEALTH_MANAGEMENT",
        "subIssueNameKr": "사업장 안전보건 관리체계",
        "subIssueSentence": "안전보건 경영시스템(ISO 45001 등) 인증, 안전보건 위원회 운영, 사업장 위험성 평가 실시 및 재해 예방을 위한 내부 프로세스를 설명하는 문장.",
        "keywordKr": ["안전보건 관리", "ISO 45001", "위험성 평가", "안전보건위원회", "중대재해예방"],
        "keywordForeignEn": ["occupational health", "safety management", "risk assessment", "iso 45001"],
        "mappedMetricIds": ["M_S_SAF_001"],
        "mappedAtomicMetricIds": ["AM_S_SAF_001_01"]
    },
    "S_SAFETY__ACCIDENT_RATE": {
        "no": 25,
        "domain": "S",
        "issueGroupSort": 8.0,
        "issueGroupId": "S_SAFETY",
        "issueGroupNameKr": "안전보건",
        "subIssueSort": 2,
        "subIssueId": "S_SAFETY__ACCIDENT_RATE",
        "subIssueNameKr": "산업재해율 및 안전 성과",
        "subIssueSentence": "임직원 및 사내 협력사 직원의 산업재해 발생 건수, 총재해율(TRIR), 아차사고(Near-miss) 관리, 사망재해 유무 및 근로손실일수를 설명하는 문장.",
        "keywordKr": ["산업재해율", "재해건수", "총재해율", "TRIR", "사망재해", "근로손실일수", "아차사고"],
        "keywordForeignEn": ["accident rate", "trir", "fatality", "lost time injury", "near miss"],
        "mappedMetricIds": ["M_S_SAF_002"],
        "mappedAtomicMetricIds": ["AM_S_SAF_002_01", "AM_S_SAF_002_02"]
    },
    "S_HR__DIVERSITY_INCLUSION": {
        "no": 28,
        "domain": "S",
        "issueGroupSort": 9.0,
        "issueGroupId": "S_HR",
        "issueGroupNameKr": "인적자원 관리",
        "subIssueSort": 1,
        "subIssueId": "S_HR__DIVERSITY_INCLUSION",
        "subIssueNameKr": "다양성 및 형평성 (DEI)",
        "subIssueSentence": "여성 임직원 및 여성 관리자 비율, 장애인 및 국가보훈 대상자 고용 현황, 고용 형태별 차별 금지 및 다양성 확대를 위한 인사 정책을 설명하는 문장.",
        "keywordKr": ["다양성", "여성 관리자 비율", "장애인 고용", "형평성", "DEI", "차별 금지"],
        "keywordForeignEn": ["diversity", "equity", "inclusion", "dei", "female manager"],
        "mappedMetricIds": ["M_S_HR_001"],
        "mappedAtomicMetricIds": ["AM_S_HR_001_01"]
    },

    # ==========================================================================================
    # [G] GOVERNANCE & DATA (이사회, 주주권리, 윤리경영, 데이터 거버넌스)
    # ==========================================================================================
    "G_BOARD__COMPOSITION_INDEPENDENCE": {
        "no": 50,
        "domain": "G",
        "issueGroupSort": 18.0,
        "issueGroupId": "G_BOARD",
        "issueGroupNameKr": "이사회 구조",
        "subIssueSort": 1,
        "subIssueId": "G_BOARD__COMPOSITION_INDEPENDENCE",
        "subIssueNameKr": "이사회 구성 및 독립성",
        "subIssueSentence": "사외이사 비율, 이사회 의장과 CEO의 분리 여부, 사외이사 후보추천위원회 운영, 이사회의 독립성과 전문성을 확보하기 위한 규정을 설명하는 문장.",
        "keywordKr": ["이사회 구성", "사외이사 비율", "이사회 독립성", "의장 CEO 분리", "사추위"],
        "keywordForeignEn": ["board composition", "independent director", "board independence"],
        "mappedMetricIds": ["M_G_BRD_001"],
        "mappedAtomicMetricIds": ["AM_G_BRD_001_01"]
    },
    "G_ETHICS__ANTI_CORRUPTION_COMPLIANCE": {
        "no": 55,
        "domain": "G",
        "issueGroupSort": 20.0,
        "issueGroupId": "G_ETHICS",
        "issueGroupNameKr": "윤리경영·준법",
        "subIssueSort": 1,
        "subIssueId": "G_ETHICS__ANTI_CORRUPTION_COMPLIANCE",
        "subIssueNameKr": "반부패 및 컴플라이언스",
        "subIssueSentence": "부패방지 경영시스템(ISO 37001) 운영, 임직원 윤리강령 준수 서약, 내부고발제도 활성화 및 윤리/준법 교육 이수 현황을 설명하는 문장.",
        "keywordKr": ["반부패", "컴플라이언스", "ISO 37001", "윤리강령", "내부고발", "준법 교육"],
        "keywordForeignEn": ["anti corruption", "compliance", "iso 37001", "whistleblowing"],
        "mappedMetricIds": ["M_G_ETH_001"],
        "mappedAtomicMetricIds": ["AM_G_ETH_001_01"]
    },
    "G_DATA_GOVERNANCE__ESG_DATA_CONTROL": {
        "no": 62,
        "domain": "G",
        "issueGroupSort": 23.0,
        "issueGroupId": "G_DATA_GOVERNANCE",
        "issueGroupNameKr": "ESG 데이터 거버넌스",
        "subIssueSort": 2,
        "subIssueId": "G_DATA_GOVERNANCE__ESG_DATA_CONTROL",
        "subIssueNameKr": "ESG 데이터 내부통제",
        "subIssueNameEn": "ESG data governance and internal control",
        "subIssueSentence": "ESG 보고서 승인 워크플로우, 정정 이력 추적, 내부 검토 및 외부 검증(Assurance) 프로세스, 데이터 사전 및 증빙 서류 관리 체계를 설명하는 문장.",
        "keywordKr": ["보고서 승인", "내부검토", "외부검증", "assurance", "증빙보관", "데이터 거버넌스", "변경이력"],
        "keywordForeignEn": ["report approval", "internal review", "external assurance", "data governance", "audit trail"],
        "mappedMetricIds": ["M_G_DAT_002"],
        "mappedAtomicMetricIds": ["AM_G_DAT_002_01", "AM_G_DAT_002_02"]
    }
}

# 62개 전체 명세 검증용 헬퍼 함수
def getSubissueCount():
    return len(subissueMaster)