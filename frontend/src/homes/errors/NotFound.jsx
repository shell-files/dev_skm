import '@styles/error.css'


const NotFound = () => {

  return (
    <div id="not_found_wrap">
      <div className="error-container">
        <div className="error-code">404</div>
        <div className="error-msg">요청하신 페이지를 찾을 수 없습니다.</div>
        <p>입력하신 주소가 정확한지 다시 한번 확인해 주세요.</p>
        <a href="/" className="btn-home">메인으로 돌아가기</a>
      </div>
    </div>

  )
}

export default NotFound