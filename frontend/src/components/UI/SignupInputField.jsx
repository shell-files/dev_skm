/**
 * SignupInputField.jsx
 * 레이어: Component (UI)
 * 역할: 회원가입 폼의 입력 필드 — 라벨, 유효성 메시지, 비밀번호 표시 토글을 포함한 공통 입력 컴포넌트.
 */
const SignupInputField = ({
    label,
    name,
    type = "text",
    value,
    onChange,
    onBlur,
    placeholder,
    error,
    success,
    autoComplete = "off",
    readOnly = false
}) => {
    return (
        <div className="input-group">
            <label>{label}</label>

            <div className="input-wrap">
                <input
                    type={type}
                    name={name}
                    value={value}
                    onChange={onChange}
                    onBlur={onBlur}
                    placeholder={placeholder}
                    autoComplete={autoComplete}
                    readOnly={readOnly}
                />

                {!error && success && (
                    <p className="success">{success}</p>
                )}

                {error && (
                    <p className="error">{error}</p>
                )}
            </div>
        </div>
    )
}

export default SignupInputField