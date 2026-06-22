<<<<<<< HEAD
/**
 * Signup.jsx
 * 레이어: Page
 * 역할: 사업자등록증 OCR 인증, 중복 검사, 업종 5단계 선택을 포함한 기업 회원가입 페이지
 */
=======
>>>>>>> origin/skm_test
// =====================================================================================
// Signup.jsx 페이지 흐름설명 (유저 행동 기준)

// 1. OCR 인증 흐름
// 파일 선택 → handleFileChange → handleUpload → OCR API 요청
// → 성공 시 formData 자동 채움 + isOcrDone = true

// 2. 중복 검사 흐름
// 이메일 입력 → handleChange → onBlur → checkEmail → emailValid 상태 변경
// 사업자번호 입력 → handleChange → onBlur → checkBusiness → businessValid 상태 변경

// 3. 회원가입 제출 흐름
// 가입 버튼 클릭 → handleSubmit 실행
// → 필수값 검증 + OCR 여부 + 중복 여부 확인
// → 성공 시 API 요청 → 완료 alert → navigate("/main")

// 4. 업종 선택 흐름
// select 5단계 선택 → addIndustry → industryCodes 배열 추가

// 5. 취소 흐름
// 취소 버튼 클릭 → handleCancel → confirm alert → navigate("/login")

// =====================================================================================
// API 연결 위치 (수정 포인트)
// =========================

// 1. OCR 업로드
// → api.post("/user", formData)

// 2. 회원가입
// → api.put("/user", payload)

// 3. 이메일 중복 검사
// → api.get("/user?email=")

// 4. 사업자번호 중복 검사
// → api.get("/user?businessNumber=")

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router'
import '@styles/SignUp.css'
import { GET, POST, PUT } from "@utils/Network";
// import ksicData from '@assets/data/ksicClassification.json';
import { showDefaultAlert, showConfirmAlert } from '@components/UI/ServiceAlert.jsx';
import SignupInputField from '@components/UI/SignupInputField'
import { useAuth } from '@hooks/AuthContext';

const Signup = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const fileInputRef = useRef(null); // 파일 선택창(input type="file")에 직접 접근하기 위한 Ref

    // --- [상태 관리: 파일 및 인증] ---
    const [fileName, setFileName] = useState(''); // 선택된 파일의 이름 표시용
    const [file, setFile] = useState(null);       // 실제 서버로 전송할 파일 객체
    const [fileId, setFileId] = useState(null);     //OCR 후 파일 ID 받기 위함
    const [isOcrDone, setIsOcrDone] = useState(false);   // 사업자 등록증 OCR 인증 완료 여부
    const [isUploading, setIsUploading] = useState(false); // OCR 업로드 중 로딩 상태
    const [isAgreed, setIsAgreed] = useState(false);     // 약관 동의 여부

    // --- [상태 관리: 중복 검사 및 에러] ---
    const [emailValid, setEmailValid] = useState(null);    // 이메일 중복 검사 결과 (null: 미검사, true: 가능, false: 중복)
    const [businessValid, setBusinessValid] = useState(null); // 사업자번호 중복 검사 결과
    const [errors, setErrors] = useState({});               // 필드별 에러 메시지 저장 객체
    const [signupLoading, setSignupLoading] = useState(false); // 최종 가입 버튼 클릭 시 로딩 상태

    // --- [상태 관리: 입력 폼 데이터] ---
    const [industryCodes, setIndustryCodes] = useState([]);
    const [sel, setSel] = useState({ large: '', medium: '', small: '', fine: '', detail: '' });
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        passwordCheck: '',
        ceoName: '',
        userName: '',
        businessNumber: '',
        companyName: '',
        openingDate: '',
        corporateNumber: '',
        headOffice: '',
        issueDate: '',
        taxName: '',
        companySize: ''

    });

    const [ksicData, setKsicData] = useState([]);

    useEffect(() => {
        (async () => {
            try {
                const res = await GET("/user");
                if (res.status) setKsicData(res.data.industryCodes);
            } catch (err) {
                console.error("데이터 로드 실패:", err);
            }
        })();
    }, []);

    const addIndustry = () => {
        if (!sel.detail) {
            return showDefaultAlert(
                "업종 선택 필요",
                "세세분류까지 모두 선택해주세요.",
                "warning"
            )
        }

        const target = ksicData.find(i =>
            i.largeCategoryName === sel.large &&
            i.mediumCategoryName === sel.medium &&
            i.smallCategoryName === sel.small &&
            i.fineCategoryName === sel.fine &&
            i.detailCategoryName === sel.detail
        );
        // console.log("sel:", sel);
        // console.log("target:", target);
        // console.log("ksic sample:", ksicData[0]);
        if (target) {
            const code = target.standardIndustryClassification;
            if (industryCodes.includes(code)) {
                return showDefaultAlert(
                    "중복 업종",
                    "이미 추가된 업종입니다.",
                    "warning"
                );
            }
            setIndustryCodes([...industryCodes, code]); // 코드만 배열에 추가
            // 선택 창 초기화
            setSel({ large: '', medium: '', small: '', fine: '', detail: '' });
        }
    };

    // 필드별 필수 입력 경고 메시지 정의
    const requiredFields = {
        email: "이메일은 필수입니다.",
        password: "비밀번호는 필수입니다.",
        ceoName: "대표자명은 필수입니다.",
        businessNumber: "사업자번호는 필수입니다.",
        companyName: "법인명은 필수입니다.",
        openingDate: "개업일은 필수입니다.",
        // corporateNumber: "법인 등록번호는 필수입니다.",
        headOffice: "본점 소재지는 필수입니다.",
        issueDate: "발행일은 필수입니다.",
        taxName: "발행처는 필수입니다.",
    };

    // 현재 페이지가 통신 중(로딩 중)인지 확인하는 변수
    const isLoading = isUploading || signupLoading;

    // --- [로직: 유효성 검사] ---
    const passwordRegex =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&])[A-Za-z\d!@#$%^&]{10,}$/;

    /**
     * 특정 필드에 포커스가 나갔을 때(onBlur) 값의 유무와 형식을 체크합니다.
     */
    const validateField = (name, value) => {
        if (name === "corporateNumber") return;
        let message = "";
        // 1. 빈 값 체크
        if (!value) {
            message = requiredFields[name] || "필수 항목입니다.";
        }
        // 이메일 검증
        if (name === "email" && value) {
            const regex = /\S+@\S+\.\S+/;
            if (!regex.test(value)) {
                message = "이메일 형식이 올바르지 않습니다.";
            }
        }
        // 비밀번호 정책 검증
        if (name === "password" && value) {
            if (!passwordRegex.test(value)) {
                message =
                    "비밀번호는 10자리 이상이며 대문자, 소문자, 숫자, 특수문자(!@#$%^&)를 포함해야 합니다.";
            }
        }
        // 비밀번호 확인 검증
        if (name === "passwordCheck" && value) {

            if (value !== formData.password) {
                message = "비밀번호가 일치하지 않습니다.";
            }
        }
        setErrors(prev => ({
            ...prev,
            [name]: message
        }));
    };

    // --- [로직: 입력 값 변경 핸들링] ---
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        // 이메일이나 사업자번호가 수정되면 중복 검사 결과를 초기화
        if (name === "email") setEmailValid(null);
        if (name === "businessNumber") setBusinessValid(null);

        // 타이핑 시 해당 필드의 에러 메시지 제거
        setErrors(prev => ({ ...prev, [name]: "" }));
    };

    // --- [로직: 파일 업로드 및 OCR] ---
    // 가짜 '파일 선택' 버튼 클릭 시 실제 숨겨진 input을 클릭하게 함
    const handleFileBtnClick = () => fileInputRef.current.click();

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            setFileName(selectedFile.name);
            setIsOcrDone(false); // 파일을 새로 고르면 다시 인증받도록 초기화
        }
    };

    /************************************
    // 1. handleUpload
    // 설명: 사업자등록증 OCR 업로드 실행
    // 역할:
    // - 파일 존재 여부 검사
    // - 파일 형식 검증 (jpg, png, pdf)
    // - API 요청 또는 더미 처리
    // - 성공 시 formData 자동 입력 + fileId 저장 + OCR 완료 상태 변경
    ************************************/
    const handleUpload = async () => {
        if (!file) {
            // ----------- 커스텀 알럿 추가 ----------
            showDefaultAlert(
                "파일이 첨부되지 않았습니다",
                "기업 회원가입을 위해 <span class='text-point'>사업자등록증</span> 첨부가 필요합니다.\n"+
                "파일 선택 후 다시 등록 버튼을 눌러주세요.",
                "warning"
            )
            // alert("파일을 먼저 선택해주세요.");
            return;
        }
        setIsUploading(true);

        // 실제 모드: FormData에 파일을 담아 API 전송
        try {
            const formDataToSend = new FormData();
            const ext = file.name.split('.').pop().toLowerCase();
            const allowed = ['jpg', 'jpeg', 'png', 'pdf'];

            if (!allowed.includes(ext)) {
                showDefaultAlert(
                    "파일 형식 오류",
                    "jpg, jpeg, png, pdf 파일만 업로드 가능합니다.",
                    "error"
                )
                setIsUploading(false);
                return;
            }

            formDataToSend.append("file", file);
            formDataToSend.append("fileName", file.name);
            formDataToSend.append("fileExt", ext);

            const res = await POST("/user", formDataToSend, true);
            if (res.status === true) {
                const data = res.licenseData;
                setFormData(prev => ({
                    ...prev,
                    businessNumber: data["사업자등록번호"] || "",
                    companyName: data["상호"] || "",
                    ceoName: data["성명"] || "",
                    openingDate: data["개업연월일"] || "",
                    headOffice: data["사업장소재지"] || "",
                    issueDate: data["발급날짜"] || "",
                    taxName: data["발급세무서"] || ""
                }));

                // ✅ 안전 처리
                if (res.fileId) {
                    setFileId(res.fileId.id);
                }

                setIsOcrDone(true);
            } else {
                showDefaultAlert(
                    "OCR 실패",
                    "사업자등록증 정보를 읽지 못했습니다.",
                    "error"
                )
            }
        } catch (err) {

            // ----------- 커스텀 알럿 추가 ----------
            showDefaultAlert(
                "인증 실패",
                "사업자등록증 OCR 인증에 실패하였습니다.\n"+
                "잠시 후 다시 시도해주세요.",
                "error"
            )
            // alert("서버 오류가 발생했습니다.");
        } finally {
            setIsUploading(false);
        }
    };

    /************************************
    // 2. checkEmail
    // 설명: 이메일 중복 검사 API 호출
    // 결과:
    // - true: 사용 가능
    // - false: 중복
    // → emailValid 상태 업데이트
    ************************************/
    const checkEmail = async () => {
        if (!formData.email || errors.email) return;
        try {
            const res = await POST('/verification', {email: formData.email});
            setEmailValid(res.status); // true면 사용 가능, false면 중복
        } catch (err) {
            console.error("이메일 중복 검사 에러:", err);

        }
    };

    /************************************
    // 2-1. checkBusiness
    // 설명: 사업자등록번호 중복 검사 API 호출
    // 결과:
    // - true: 사용 가능
    // - false: 중복
    // → businessValid 상태 업데이트
    ************************************/
    const checkBusiness = async () => {
        if (!formData.businessNumber) return;

        try {
            // 명세서: GET /verification?businessNumber=값
            const res = await POST('/verification', {
                businessNumber: formData.businessNumber
            });
            setBusinessValid(res.data.status);
        } catch (err) {
            console.error("사업자번호 중복 검사 에러:", err);
        }
    };

    /************************************
    // 3. handleSubmit
    // 설명: 회원가입 최종 제출 핸들러
    // 역할:
    // - 필수값 검증
    // - OCR 완료 여부 체크
    // - 중복 검사 결과 확인
    // - payload 가공 (숫자 변환 등)
    // - API 요청
    // - 성공 시 confirm alert → 메인 페이지 이동
    ************************************/
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!passwordRegex.test(formData.password)) {
            return showDefaultAlert(
                "비밀번호 형식 오류",
                "비밀번호는 10자리 이상이며 \n 대문자, 소문자, 숫자, 특수문자(!@#$%^&)를 포함해야 합니다.",
                "warning"
            );
        }
        if (formData.password !== formData.passwordCheck) {
            return showDefaultAlert(
                "비밀번호 불일치",
                "비밀번호 확인이 일치하지 않습니다.",
                "warning"
            );
        }
        // 1️⃣ 즉시 차단 (UX alert)
        if (industryCodes.length === 0) {
            return showDefaultAlert("업종 선택 필요", "최소 하나 이상의 업종을 선택해주세요.", "warning");
        }
        if (!formData.companySize) {
            return showDefaultAlert("기업 규모 선택 필요", "기업 규모를 선택해주세요.", "warning");
        }
        if (!isAgreed) {
            return showDefaultAlert("약관 동의 필요", "서비스 이용을 위해 약관에 동의해주세요.", "warning");
        }
        // if (!isOcrDone || !fileId) {
        //     return showDefaultAlert("OCR 필요", "사업자 인증을 완료해주세요.", "warning");
        // }
        if (emailValid === false) {
            return showDefaultAlert("이메일 중복", "이미 사용중인 이메일입니다.", "error");
        }
        if (businessValid === false) {
            return showDefaultAlert("사업자번호 확인", "이미 사용중인 사업자번호입니다.", "error");
        }
        setSignupLoading(true);
        // 2️⃣ 폼 에러 표시용 검증
        const newErrors = {};
        Object.keys(requiredFields).forEach(key => {
            if (!formData[key]) {
                newErrors[key] = requiredFields[key];
            }
        });
        if (!file) newErrors.file = "파일 업로드 필수";
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }
        // 3️⃣ API 요청
        try {
            const res = await PUT("/user", {
                ...formData,
                licensefileId: fileId,
                industryList: industryCodes,
                agreed: isAgreed,
                businessNumber: Number(formData.businessNumber.replace(/-/g, "")),
                corporateNumber: Number(formData.corporateNumber.replace(/-/g, "")),
            });
            console.log(res);
            if (res.status) {
                // 회원가입 후 자동 로그인
                // const loginRes = await POST("/auth", {
                //     email: formData.email,
                //     password: formData.password,
                // });

                // if (loginRes.status === true) {
                //     login(loginRes.data);
                // }

                await showDefaultAlert(
                    "회원가입 완료",
                    "회원가입이 완료되었습니다.",
                    "success"
                );
                navigate("/login");
            } else {
                showDefaultAlert("가입 실패", "입력 정보를 다시 확인해주세요.", "error");
            }
        } catch (err) {
            showDefaultAlert("서버 오류", "잠시 후 다시 시도해주세요.", "error");
            console.error("회원가입 에러:", err);
        } finally {
            setSignupLoading(false);
        }
    };

    const handleCancel = async () => {
        const isConfirmed = await showConfirmAlert(
            "가입 취소",
            "가입을 취소하시겠습니까?\n" +
            "지금까지 입력한 정보가 모두 사라집니다.",
            "warning"
        )
        if (isConfirmed) {
            navigate("/")
        }
        // if (window.confirm("가입을 취소하시겠습니까? 입력한 정보가 사라집니다.")) {
        //     navigate(-1);
        // }
    };

    // 반복되는 사업자 정보 입력 칸을 효율적으로 렌더링하기 위한 배열
    const bizFields = [
        { label: "법인명(단체명)", name: "companyName" },
        { label: "대표자명", name: "ceoName" },
        { label: "개업 연월일", name: "openingDate" },
        { label: "법인 등록번호", name: "corporateNumber" },
        { label: "본점 소재지", name: "headOffice" },
        { label: "발행일", name: "issueDate" },
        { label: "발행처", name: "taxName" },
    ];

    // --- [렌더링 구역] ---
    return (
        <div id="signup_page">
            <div className='signup-wrapper'>
                <div className="signup-container">
                    {/* 상단 제목: 더미 모드일 때 빨간 글씨로 표시 */}
                    <h1>회원가입</h1>

                    <form onSubmit={handleSubmit} autoComplete="off">

                        {/* 1. 가입 정보 섹션 (이메일, 비밀번호) */}
                        <section className="form-section">
                            <h2 className="section-title">가입 정보</h2>
                            {/* 이름 입력 */}
                            <SignupInputField label="성명" name="userName" value={formData.userName} onChange={handleChange}
                                onBlur={(e) => validateField("userName", e.target.value)} placeholder="ESG 담당자 이름을 입력해주세요" error={errors.userName}/>

                            {/* 이메일 입력 */}
                            <SignupInputField label="이메일" type="email" name="email" value={formData.email}
                                onChange={handleChange} onBlur={(e) => {validateField("email", e.target.value);checkEmail()}}
                                placeholder="회사의 대표 이메일을 입력해주세요" error={errors.email} success={emailValid === true ? "사용 가능한 이메일입니다." : ""}/>

                            {/* 비밀번호 입력 */}
                            <SignupInputField label="비밀번호" type="password" name="password" value={formData.password}
                                onChange={handleChange} onBlur={(e) => validateField("password", e.target.value)}
                                placeholder="사용할 비밀번호를 입력해주세요" error={errors.password}/>
                            <SignupInputField label="비밀번호 확인" type="password" name="passwordCheck" value={formData.passwordCheck}
                                onChange={handleChange} onBlur={(e) => validateField("password", e.target.value)}
                                placeholder="사용할 비밀번호를 확인해주세요" error={errors.password}/>
                        </section>

                        <hr className="divider" />

                        {/* 2. 사업자 정보 섹션 (파일 업로드 및 OCR 결과) */}
                        <section className="form-section">
                            <h2 className="section-title">사업자 정보</h2>
                            <p className="helper-text">*사업자등록증을 업로드한 후 등록버튼을 눌러주세요</p>

                            {/* 파일 선택 및 OCR 등록 버튼 */}
                            <div className="input-group file-upload">
                                <label>사업자 등록증</label>
                                <div className="upload-controls">
                                    <input type="file" ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
                                    <input type="text" readOnly value={fileName} placeholder="선택된 파일 없음" />
                                    <button type="button" className="btn-green" onClick={handleFileBtnClick}>파일 선택</button>
                                    <button type="button" className="btn-green" onClick={handleUpload} disabled={isUploading}>
                                        {isUploading ? <span className="button-spinner" /> : "등록"}
                                    </button>
                                </div>
                            </div>
                            {errors.file && <p className="error">{errors.file}</p>}
                            {errors.ocr && <p className="error">{errors.ocr}</p>}

                            {/* 사업자 등록번호 (중복 검사 포함) */}
                            <SignupInputField label="사업자 등록번호" name="businessNumber" value={formData.businessNumber}
                                onChange={handleChange} onBlur={(e) => {validateField("businessNumber", e.target.value);checkBusiness()}}
                                placeholder="사업자 등록번호를 입력해주세요" error={errors.businessNumber} success={businessValid === true ? "사용 가능" : ""}
                            />

                            {/* 나머지 OCR 연동 필드들 (반복문 처리) */}
                            {bizFields.map((field) => (
                                <SignupInputField key={field.name} label={field.label} name={field.name} value={formData[field.name]} onChange={handleChange}
                                onBlur={(e) => validateField(field.name, e.target.value)} placeholder={`${field.label}을(를) 입력해주세요`}
                                    error={errors[field.name]}/>
                            ))}
                            {/* 기업규모 셀렉트 박스 */}
                            <div className="input-group">
                                <label>기업 규모</label>
                                <div className="input-wrap">   {/* ✅ 이렇게 */}
                                    <select
                                        name="companySize"
                                        value={formData.companySize}
                                        onChange={(e) => setFormData({...formData, companySize: e.target.value})}
                                    >
                                        <option value="">규모를 선택해주세요.</option>
                                        <option value="소기업">소기업</option>
                                        <option value="중기업">중기업</option>
                                        <option value="중견기업">중견기업</option>
                                        <option value="대기업">대기업</option>
                                    </select>
                                </div>
                            </div>
                            {/* 업종 5단계 선택 UI 추가 */}
                            <div className="industry-selection-wrapper">
                                <h3 className="sub-title">업종 추가 (표준산업분류 기준)</h3>

                                <div className="select-step-group">
                                    {/* 대분류 */}
                                    <select value={sel.large} onChange={(e) => setSel({...sel, large: e.target.value, medium:'', small:'', fine:'', detail:''})}>
                                        <option value="">대분류 선택</option>
                                        {[...new Set(ksicData.map(i => i.largeCategoryName))].map(name => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>

                                    {/* 중분류 -filtered 리스트에서 중복 제거 */}
                                    <select
                                        disabled={!sel.large}
                                        value={sel.medium}
                                        onChange={(e) => setSel({...sel, medium: e.target.value, small:'', fine:'', detail:''})}
                                    >
                                        <option value="">중분류 선택</option>
                                        {[...new Set(ksicData
                                            .filter(i => i.largeCategoryName === sel.large)
                                            .map(item => item.mediumCategoryName)
                                        )].map(name => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>

                                    {/* 소분류 - filtered 리스트에서 중복 제거 */}
                                    <select
                                        disabled={!sel.medium}
                                        value={sel.small}
                                        onChange={(e) => setSel({...sel, small: e.target.value, fine:'', detail:''})}
                                    >
                                        <option value="">소분류 선택</option>
                                        {[...new Set(ksicData
                                            .filter(i => i.mediumCategoryName === sel.medium)
                                            .map(item => item.smallCategoryName)
                                        )].map(name => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>

                                    {/* 세분류 - filtered 리스트에서 중복 제거 */}
                                    <select
                                        disabled={!sel.small}
                                        value={sel.fine}
                                        onChange={(e) => setSel({...sel, fine: e.target.value, detail:''})}
                                    >
                                        <option value="">세분류 선택</option>
                                        {[...new Set(ksicData
                                            .filter(i => i.smallCategoryName === sel.small)
                                            .map(item => item.fineCategoryName)
                                        )].map(name => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>

                                    {/* 세세분류 (최종) - 마지막 단계는 보통 유니크하므로 그대로 두거나 동일하게 처리 */}
                                    <select
                                        disabled={!sel.fine}
                                        value={sel.detail}
                                        onChange={(e) => setSel({...sel, detail: e.target.value})}
                                    >
                                        <option value="">세세분류 선택</option>
                                        {[...new Set(ksicData
                                            .filter(i => i.fineCategoryName === sel.fine)
                                            .map(item => item.detailCategoryName)
                                        )].map(name => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>

                                {/* 추가된 업종 코드 리스트 표시 */}
                                </div>
                                <div className="selected-codes-container">
                                    {industryCodes.map((code, idx) => (
                                        <div key={idx} className="code-tag">
                                            업종 : {ksicData.find(i => i.standardIndustryClassification === code)?.detailCategoryName}
                                            <button type="button" onClick={() => setIndustryCodes(industryCodes.filter((_, i) => i !== idx))}>x</button>
                                        </div>
                                    ))}
                            </div>
                            <button type="button" className="btn-add" onClick={addIndustry}>업종 추가</button>
                            </div>

                        </section>

                        <hr className="divider" />

                        {/* 3. 약관 동의 섹션 */}
                        <section className="form-section">
                            <h2 className="section-title">약관</h2>
                            <div className="terms-box">
                                <h4>[제1장 일반사항]</h4>
                                <p>본 서비스는 [WITH]이 제공하는 사업자 관리 및 OCR 인식 서비스를 포함합니다.</p>
                                <h4>[제2장 개인정보 및 사업자정보 수집]</h4>
                                <p>1. 회사는 서비스 제공을 위해 이메일, 비밀번호, 사업자등록증 내 정보를 수집합니다.</p>
                                <p>2. OCR 기능을 통해 추출된 정보는 자동 입력 편의를 위해 사용됩니다.</p>
                                <h4>[제3장 정보의 보유 및 이용기간]</h4>
                                <p>회원의 개인정보는 원칙적으로 회원 탈퇴 시 지체 없이 파기합니다.</p>
                            </div>
                            {/* 동의 라디오 버튼 */}
                            <div className="radio-group">
                                <label><input type="radio" name="agree" checked={isAgreed === true} onChange={() => setIsAgreed(true)} /> 동의함</label>
                                <label><input type="radio" name="agree" checked={isAgreed === false} onChange={() => setIsAgreed(false)} /> 동의안함</label>
                            </div>
                            {errors.agree && <p className="error">{errors.agree}</p>}
                        </section>

                        <hr className="divider" />

                        {/* 4. 하단 액션 버튼 (가입, 취소) */}
                        <div className="action-buttons">
                            <button type="submit" className="btn-green btn-large" disabled={isLoading}>
                                {signupLoading ? <span className="button-spinner" /> : "가입"}
                            </button>
                            <button type="button" className="btn-green btn-large" onClick={handleCancel}>취소</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default Signup;