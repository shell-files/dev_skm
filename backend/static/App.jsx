// 기본 Alert 모달 (확인 버튼만)
const AlertOverlay = ({alertMessage, setIsAlert}) => {
  const closeAlert = () => {
    setIsAlert(false);
    window.location.href = "http://weareithero.cloud";
  }
  return (
    <div id="alertOverlay" className="alert-overlay">
        <div className="alert-box">
            <p>{alertMessage}</p>
            <div className="alert-buttons">
                <button onClick={closeAlert}>확인</button>
            </div>
        </div>
    </div>
  );
}

// Confirm 모달 (확인/취소 버튼)
const ConfirmOverlay = ({confirmMessage, setIsConfirm}) => {
  const confirmOk = () => {
    setIsConfirm(false);
    window.location.href = "http://weareithero.cloud";
  }
  return (
    <div id="confirmOverlay" className="alert-overlay">
        <div className="alert-box">
            <p>{confirmMessage}</p>
            <div className="alert-buttons">
                <button onClick={confirmOk}>확인</button>
                <button className="btn-cancel" onClick={()=>setIsConfirm(false)}>취소</button>
            </div>
        </div>
    </div>
  );
}

const App = () => {
  const [isSave, setIsSave] = React.useState(false);
  const [isAlert, setIsAlert] = React.useState(false);
  const [isConfirm, setIsConfirm] = React.useState(false);
  const [user, setUser] = React.useState({companyName: "", email: "", name: "", password: "", passwordConfirm: ""});
  const [message, setMessage] = React.useState("");
  const [path, setPath] = React.useState(document.location.pathname);
  const handleSignUp = async () => {
    axios.put(path, user)
    .then(response => {
      setMessage(response.data.message);
      setIsAlert(true);
    })
    .catch(error => {
      console.error("Error:", error);
    });    
  }

  const handleCancel = async () => {
    setMessage("가입을 취소하시겠습니까?");
    setIsConfirm(true);
  }

  const handlePasswordCheck = (e) => {
    const { value } = e.target;
    setIsSave(value === user.password);
  }

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setUser(prev => ({ ...prev, [id]: value }));
  }

  React.useEffect(()=>{
    axios.post(path)
    .then(response => {
      if (response.data.status) {
        setUser(response.data.data);
      } 
    })
    .catch(error => {
      console.error("Error:", error);
    });
  }, []);
  return (
    <>
      {isAlert && <AlertOverlay alertMessage={message} setIsAlert={setIsAlert} />}
      {isConfirm && <ConfirmOverlay confirmMessage={message} setIsConfirm={setIsConfirm} />}
      <h1>회원가입</h1>
      <form>
          <section className="form-section">
              <h2 className="section-title">가입 정보</h2>
              <div className="input-group">
                  <label>회사명</label>
                  <input type="text" id="companyName" readOnly name="companyName" value={user.companyName} onChange={handleInputChange} />
              </div>
              <div className="input-group">
                  <label>이메일</label>
                  <input type="email" id="email" readOnly name="email" value={user.email} onChange={handleInputChange} />
              </div>
              <div className="input-group">
                  <label>이름</label>
                  <input type="text" id="name" placeholder="이름을 입력해주세요" name="name" value={user.name} onChange={handleInputChange} />
              </div>
              <div className="input-group">
                  <label>비밀번호</label>
                  <input type="password" id="password" placeholder="비밀번호를 입력해주세요" name="password" value={user.password} onChange={handleInputChange} />
              </div>
              <div className="input-group">
                  <label>비밀번호 확인</label>
                  <input type="password" id="passwordConfirm" placeholder="비밀번호를 다시 입력해주세요" name="passwordConfirm" onChange={handlePasswordCheck} />
              </div>
          </section>
          <hr className="divider" />
          <div className="action-buttons">
              <button type="button" className="btn-green btn-large" onClick={handleSignUp} disabled={!isSave}>가입</button>
              <button type="button" className="btn-green btn-large" onClick={handleCancel}>취소</button>
          </div>
      </form>
    </>
  );
}
