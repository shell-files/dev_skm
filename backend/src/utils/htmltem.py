from src.utils.settings import settings
# html1: ?щ궡 吏곸썝 珥덈?
# html2: 而⑥꽕?댄듃 珥덈? (?좉퇋: type 2, 湲곗〈: type 3)
# html3: ?꾩떆 鍮꾨?踰덊샇 諛쒖넚
# html4: ?묐젰??珥덈? 硫붿씪 諛쒖넚

def html1(companyName, uuid):
    return f"""
      <!DOCTYPE html>
      <html>
      <head>
          <meta charset="UTF-8">
          <title>WITH ?쒕퉬???뚮┝</title>
      </head>
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="padding: 40px 0;">
        <tr>
          <td align="center">
            <table width="600" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #eeeeee; border-radius: 12px; overflow: hidden;">
              <tr><td height="5" style="background-color: #28a745;"></td></tr>
              
              <tr>
                <td style="padding: 40px; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
                  <h1 style="font-size:24px; color:#333333; margin-bottom:24px; text-align:center;">
                      ESG ?뚮옯??珥덈? ?덈궡
                  </h1>
                  
                  <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                    ?덈뀞?섏꽭??<br>
                    <strong>{companyName}</strong>??ESG ?곗씠??愿由?諛??묒뾽???꾪븳<br>
                    <strong>WITH ESG ?뚮옯??/strong>??珥덈??섏뀲?듬땲??<br>
                    ?꾨옒 踰꾪듉???대┃?섏뿬 ?뚯썝媛?낆쓣 ?꾨즺?섍퀬 ESG ?낅Т瑜??쒖옉??蹂댁꽭??
                  </p>
                  <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                    <ul style="margin-bottom: 20px; padding: 0; list-style: none; font-size: 14px; color: #666666;">
                      <li style="margin-bottom: 20px;">
                        <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;"> ?뚯냽 ?뚯궗</p>
                        <span style="font-size:20px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;"> {companyName}</span>
                      </li>
                      <li style="margin-bottom: 8px;">?뷂툘 ?댁슜 踰붿쐞: ESG ?곗씠??愿由?諛??묒뾽 湲곕뒫 ?쒓났</li>
                      <li>?뷂툘 媛???덉감: ?대쫫, 鍮꾨?踰덊샇 ?ㅼ젙 ??利됱떆 ?댁슜 媛??/li>
                    </ul>
                  </div>
                  <div style="text-align: center;">
                    <a href="{settings.host_ip}/invite/{uuid}" style="background-color: #28a745; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; font-size: 16px;">
                      ?뚯썝媛???섎윭媛湲?
                    </a>
                  </div>
                  
                  <p style="font-size: 13px; color: #999999; margin-top: 30px; text-align: center;">
                    蹂?硫붿씪? 珥덈?諛쏆? 遺꾧퍡留?諛쒖넚?섏뿀?듬땲??<br>
                    濡쒓렇?몄씠 ?섏? ?딄굅??臾몄젣媛 諛쒖깮?섎㈃ 愿由ъ옄?먭쾶 臾몄쓽??二쇱꽭??
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
      </html>
    """

def html2(type, companyName, uuid):
    if type == 2:
        consultantHtml = f"""
          <div style="background-color:#ffffff; border:3px solid #03a94d; border-radius:8px; padding:20px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                  ???좉퇋 ?ъ슜??
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  <strong>?뚯썝媛????ESG ?뚮옯?쇱뿉 ?묒냽?섏뿬</strong> ?묒뾽???쒖옉?섏떎 ???덉뒿?덈떎.
              </p>
          </div>
        """
        url = f"{settings.host_ip}/invite/{uuid}"
    elif type == 3:
        consultantHtml = f"""
          <div style="background-color:#fff; border:3px solid #03a94d; border-radius:8px; padding:20px; margin-bottom:15px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                  ??湲곗〈 怨꾩젙 ?ъ슜??
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  濡쒓렇?명븯硫?<strong>ESG ?꾨줈?앺듃 諛??곗씠???묎렐 沅뚰븳???먮룞?쇰줈 ?곌껐?⑸땲??</strong>
              </p>
          </div>
        """
        url = f"{settings.host_ip}/login"
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>WITH ?쒕퉬???묒뾽 珥덈?</title>
</head>

<body style="margin:0; padding:40px 0; background-color:#ffffff;">

<table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
        <td align="center">

            <table width="600" border="0" cellpadding="0" cellspacing="0"
                style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

                <!-- ?곷떒 ?ъ씤??-->
                <tr>
                    <td height="5" style="background-color:#03a94d;"></td>
                </tr>

                <tr>
                    <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

                        <h1 style="font-size:22px; color:#333333; margin-bottom:24px; text-align:center;">
                            ESG ?뚮옯???묒뾽 珥덈? ?덈궡
                        </h1>

                        <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                            洹?щ? <strong>{companyName}</strong>??ESG ?꾨줈?앺듃 ?묒뾽???꾪븳<br>
                            <strong>WITH ESG ?뚮옯??/strong>??怨듭떇 ?묐젰??而⑥꽕?댄듃)濡?珥덈??섏??듬땲??
                        </p>

                        <!-- ?덈궡 諛뺤뒪 -->
                        <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                            <h3 style="margin-top:0; font-size:15px; color:#333333;">
                                [ESG ?뚮옯???댁슜 ?덈궡]
                            </h3>
                            <ul style="margin:10px 0 0 0; padding:0; list-style:none; font-size:14px; color:#333333; line-height:1.8;">
                                {consultantHtml}
                            </ul>
                        </div>

                        <p style="font-size:14px; color:#333333; text-align:center; margin-bottom:25px;">
                            ?먰솢???낅Т ?묒뾽???꾪빐 ?꾨옒 踰꾪듉???대┃?섏뿬 ?쒖뒪?쒖뿉 ?묒냽??二쇱떗?쒖삤.
                        </p>

                        <!-- 踰꾪듉 -->
                        <div style="text-align:center;">
                            <a href="{url}"
                                style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                                ESG ?뚮옯???묒냽?섍린
                            </a>
                        </div>
                        
                        <!-- ?덈궡臾?-->
                        <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                            <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                                * 蹂?硫붿씪? ?낅Т 紐⑹쟻?쇰줈 諛쒖넚??蹂댁븞 硫붿씪?낅땲??<br>
                                * ?쒖뒪???댁슜 愿??臾몄쓽: platformanagers@gmail.com
                            </p>
                        </div>

                    </td>
                </tr>

                <!-- ?명꽣 -->
                <tr>
                    <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
                        짤 2026 WITH Platform. All rights reserved.
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
  return f"""
  <!DOCTYPE html>
  <html>
  <head>
      <meta charset="UTF-8">
      <title>WITH ?쒕퉬???뚮┝</title>
  </head>

  <body style="margin:0; padding:40px 0; background-color:#ffffff;">

  <table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">

        <table width="600" border="0" cellpadding="0" cellspacing="0"
          style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

          <!-- ?곷떒 ?ъ씤??-->
          <tr>
            <td height="5" style="background-color:#03a94d;"></td>
          </tr>
          
          <tr>
            <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

              <h1 style="font-size:22px; color:#333333; margin-bottom:20px; text-align:center;">
                ?꾩떆 鍮꾨?踰덊샇 諛쒓툒 ?덈궡
              </h1>
              
              <p style="font-size:15px; color:#333333; line-height:1.6; text-align:center;">
                ?덈뀞?섏꽭??br>
                ?붿껌?섏떊 鍮꾨?踰덊샇 李얘린???곕Ⅸ ?꾩떆 鍮꾨?踰덊샇瑜??덈궡???쒕┰?덈떎.
              </p>

              <!-- 鍮꾨?踰덊샇 諛뺤뒪 -->
              <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:30px; border-radius:8px; margin:25px 0; text-align:center;">
                <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;">
                  ?꾩떆 鍮꾨?踰덊샇
                </p>
                <span style="font-size:28px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;">
                  {tempPwd}
                </span>
              </div>

              <p style="font-size:14px; color:#333333; line-height:1.6; text-align:center; margin-bottom:30px;">
                ?덉쟾???꾪빐 濡쒓렇????<strong>留덉씠?섏씠吏 &gt; 鍮꾨?踰덊샇 蹂寃?/strong> 硫붾돱?먯꽌<br>
                諛섎뱶???덈줈??鍮꾨?踰덊샇濡?蹂寃쏀빐 二쇱떆湲?諛붾엻?덈떎.
              </p>

              <!-- 踰꾪듉 -->
              <div style="text-align:center;">
                <a href="http://{settings.host_ip}/login"
                  style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                  濡쒓렇???섎윭媛湲?
                </a>
              </div>
              
              <!-- ?덈궡臾?-->
              <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                  * 蹂몄씤???붿껌?섏? ?딆븯?뚯뿉????硫붿씪??諛쏆쑝?⑤떎硫? ??몄뿉 ?섑빐 怨꾩젙???꾩슜?섏뿀??媛?μ꽦???덉쑝??利됱떆 怨좉컼?쇳꽣濡?臾몄쓽??二쇱꽭??
                </p>
              </div>

            </td>
          </tr>
          
          <!-- ?명꽣 -->
          <tr>
            <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
              짤 2026 WITH. All rights reserved.
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

  </body>
  </html>
  """

# def getHtml(data):
#   subject = None
#   body = None
#   tempPwd = data.get("tempPwd")
#   type = data.get("type")
#   email = data.get("email")
#   if type == 4:
#     subject = "?꾩떆 鍮꾨?踰덊샇 諛쒖넚"
#     body = html3(tempPwd)
#   return subject, body, email

def getHtml(data):
    type = data.get("type")
    email = data.get("email")
    uuid = data.get("uuid")

    if type == 1:
        return "ESG 플랫폼 초대 안내", html1(data.get("companyName") or "회사", uuid), email

    if type == 2:
        return "而⑥꽕?댄듃 珥덈?", html2(2, "A_GROUP", uuid), email

    if type == 3:
        return "湲곗〈 ?ъ슜??珥덈?", html2(3, "A_GROUP", uuid), email

    if type == 4:
        return "?꾩떆 鍮꾨?踰덊샇 諛쒖넚", html3(data.get("tempPwd")), email

    return None, None, email
