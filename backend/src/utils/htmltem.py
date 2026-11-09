# -*- coding: utf-8 -*-
"""
htmltem.py
레이어: Utils
역할: 초대 이메일 HTML 템플릿 생성.
"""
from src.utils.settings import settings

# html1: 신규 담당자 가입 초대
# html2: 컨설턴트 초대 (신규: type 2, 기존: type 3)
# html3: 임시 비밀번호 안내

def html1(companyName, uuid):
    """신규 담당자 가입 초대 이메일 HTML을 생성한다."""
    return f"""
      <!DOCTYPE html>
      <html lang="ko">
      <head>
          <meta charset="UTF-8">
          <title>ESG 플랫폼 담당자 가입 초대</title>
      </head>
      <body style="margin:0; padding:40px 0; background-color:#ffffff;">
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="padding: 40px 0;">
        <tr>
          <td align="center">
            <table width="600" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #eeeeee; border-radius: 12px; overflow: hidden;">
              <tr><td height="5" style="background-color: #28a745;"></td></tr>

              <tr>
                <td style="padding: 40px; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
                  <h1 style="font-size:24px; color:#333333; margin-bottom:24px; text-align:center;">
                    ESG 플랫폼 담당자 가입 초대
                  </h1>

                  <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                    안녕하세요.<br>
                    <strong>{companyName}</strong>의 ESG 데이터 수집 및 보고서 작성을 위한<br>
                    <strong>WITH ESG 플랫폼</strong>에 초대되었습니다.<br>
                    아래 버튼을 클릭하여 회원가입을 완료하고 ESG 관리를 시작하세요.
                  </p>
                  <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                    <ul style="margin-bottom: 20px; padding: 0; list-style: none; font-size: 14px; color: #666666;">
                      <li style="margin-bottom: 20px;">
                        <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;">초대 회사</p>
                        <span style="font-size:20px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;">{companyName}</span>
                      </li>
                      <li style="margin-bottom: 8px;">부여 역할: ESG 데이터 수집 및 보고서 작성 담당자</li>
                      <li>부여 권한: 이름, 임시 비밀번호 설정 후 즉시 사용 가능</li>
                    </ul>
                  </div>
                  <div style="text-align: center;">
                    <a href="http://capybara.{settings.skm_domain}/invite/{uuid}" style="background-color: #28a745; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; font-size: 16px;">
                      회원가입 시작하기
                    </a>
                  </div>

                  <p style="font-size: 13px; color: #999999; margin-top: 30px; text-align: center;">
                    본 메일은 초대 요청에 의해 자동으로 발송되었습니다.<br>
                    로그인이 되지 않는 문제가 발생하면 관리자에게 문의해 주세요.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
      </body>
      </html>
    """

def html2(type, companyName, uuid):
    """컨설턴트 초대 이메일 HTML을 생성한다. type 2는 신규 가입, type 3은 기존 계정 안내 형식."""
    if type == 2:
        consultantHtml = f"""
          <div style="background-color:#ffffff; border:3px solid #03a94d; border-radius:8px; padding:20px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                신규 컨설턴트 안내
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  <strong>귀하를 ESG 플랫폼에 초대하여</strong> 프로젝트 지원을 시작하게 되었습니다.
              </p>
          </div>
        """
        url = f"http://capybara.{settings.domain}/invite/{uuid}"
    elif type == 3:
        consultantHtml = f"""
          <div style="background-color:#fff; border:3px solid #03a94d; border-radius:8px; padding:20px; margin-bottom:15px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                기존 사용자 프로젝트 참여 안내
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  로그인하시면 <strong>ESG 프로젝트 및 데이터 업무가 자동으로 연결됩니다.</strong>
              </p>
          </div>
        """
        url = f"{settings.host_ip}"
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>WITH 플랫폼 프로젝트 초대</title>
</head>

<body style="margin:0; padding:40px 0; background-color:#ffffff;">

<table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
        <td align="center">

            <table width="600" border="0" cellpadding="0" cellspacing="0"
                style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

                <!-- 상단 강조선 -->
                <tr>
                    <td height="5" style="background-color:#03a94d;"></td>
                </tr>

                <tr>
                    <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

                        <h1 style="font-size:22px; color:#333333; margin-bottom:24px; text-align:center;">
                            ESG 플랫폼 프로젝트 초대 안내
                        </h1>

                        <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                            안녕하세요. <strong>{companyName}</strong>의 ESG 프로젝트 참여를 위한<br>
                            <strong>WITH ESG 플랫폼</strong>에 컨설턴트(전문가)로 초대되었습니다.
                        </p>

                        <!-- 초대 내용 -->
                        <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                            <h3 style="margin-top:0; font-size:15px; color:#333333;">
                                [ESG 플랫폼 참여 안내]
                            </h3>
                            <ul style="margin:10px 0 0 0; padding:0; list-style:none; font-size:14px; color:#333333; line-height:1.8;">
                                {consultantHtml}
                            </ul>
                        </div>

                        <p style="font-size:14px; color:#333333; text-align:center; margin-bottom:25px;">
                            원활한 업무 진행을 위해 아래 버튼을 클릭하여 플랫폼에 접속해 주세요.
                        </p>

                        <!-- 버튼 -->
                        <div style="text-align:center;">
                            <a href="{url}"
                                style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                                ESG 플랫폼 접속하기
                            </a>
                        </div>

                        <!-- 유의사항 -->
                        <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                            <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                                * 본 메일은 업무 목적으로 자동 발송된 안내 메일입니다.<br>
                                * 플랫폼 사용 문의: platformanagers@gmail.com
                            </p>
                        </div>

                    </td>
                </tr>

                <!-- 푸터 -->
                <tr>
                    <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
                        &copy; 2026 WITH Platform. All rights reserved.
                    </td>
                </tr>

            </table>

        </td>
    </tr>
</table>

</body>
</html>
"""

def html3(tempPwd):
    """임시 비밀번호 안내 이메일 HTML을 생성한다."""
    return f"""
  <!DOCTYPE html>
  <html lang="ko">
  <head>
      <meta charset="UTF-8">
      <title>WITH 플랫폼 임시 비밀번호 안내</title>
  </head>

  <body style="margin:0; padding:40px 0; background-color:#ffffff;">

  <table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">

        <table width="600" border="0" cellpadding="0" cellspacing="0"
          style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

          <!-- 상단 강조선 -->
          <tr>
            <td height="5" style="background-color:#03a94d;"></td>
          </tr>

          <tr>
            <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

              <h1 style="font-size:22px; color:#333333; margin-bottom:20px; text-align:center;">
                임시 비밀번호 발급 안내
              </h1>

              <p style="font-size:15px; color:#333333; line-height:1.6; text-align:center;">
                안녕하세요.<br>
                요청하신 계정의 임시 비밀번호를 아래와 같이 발급해 드립니다.
              </p>

              <!-- 임시 비밀번호 표시 -->
              <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:30px; border-radius:8px; margin:25px 0; text-align:center;">
                <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;">
                  임시 비밀번호
                </p>
                <span style="font-size:28px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;">
                  {tempPwd}
                </span>
              </div>

              <p style="font-size:14px; color:#333333; line-height:1.6; text-align:center; margin-bottom:30px;">
                보안을 위해 로그인 후 <strong>마이페이지 &gt; 비밀번호 변경</strong> 메뉴에서<br>
                반드시 새로운 비밀번호로 변경해 주시기 바랍니다.
              </p>

              <!-- 버튼 -->
              <div style="text-align:center;">
                <a href="{settings.host_ip}/login"
                  style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                  로그인 하러가기
                </a>
              </div>

              <!-- 유의사항 -->
              <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                  * 본인이 요청하지 않은 경우 이 메일을 무시하셔도 됩니다. 단, 제3자에 의해 계정 변경이 시도된 가능성이 있으니 즉시 관리자에게 문의해 주세요.
                </p>
              </div>

            </td>
          </tr>

          <!-- 푸터 -->
          <tr>
            <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
              &copy; 2026 WITH. All rights reserved.
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

  </body>
  </html>
  """

def getHtml(data):
    """이메일 type(1·2·3·4)에 따라 적합한 HTML 템플릿 함수를 선택해 (제목, HTML, 수신자) 튜플을 반환한다."""
    type = data.get("type")
    email = data.get("email")
    uuid = data.get("uuid")

    if type == 1:
        return "ESG 플랫폼 담당자 가입 초대 안내", html1(data.get("companyName") or "회사", uuid), email

    if type == 2:
        return "신규 컨설턴트 초대 안내", html2(2, data.get("companyName") or "회사", uuid), email

    if type == 3:
        return "기존 사용자 프로젝트 참여 안내", html2(3, data.get("companyName") or "회사", uuid), email

    if type == 4:
        return "임시 비밀번호 발급 안내", html3(data.get("tempPwd")), email

    return None, None, email
