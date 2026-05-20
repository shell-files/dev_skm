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