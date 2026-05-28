from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional, Union, List
from datetime import date
from fastapi import UploadFile

# 공통 응답 모델 및 요청 모델 정의
def ResponseModel(status: bool, message: str="", data: dict={}):
    """ 응답 모델 """
    return {
        "status": status,
        "message": message,
        "data": data
    }

# 유저 정보 모델
class UserModel(BaseModel):
    """ auth.py 로그인 API 모델 """
    uuid: str = Field(..., description="사용자 식별에 사용되는 uuid")
    id: int = Field(..., description="사용자 ID")
    name: str = Field(..., description="사용자 이름")
    email: EmailStr = Field(..., description="사용자 이메일")
    role: str = Field(..., description="사용자 역할 리스트")
    role_name: str = Field(..., description="사용자 역할 이름 리스트")

#이메일 모델
class EmailModel(BaseModel):
   email: EmailStr = Field(..., description="비밀번호 찾기에 사용되는 이메일 모델")

# Company 정보 모델
class SignUpModel(BaseModel):
  """user.py 회원가입 통합 요청 모델"""

  # ── USER 테이블 필드
  email: EmailStr                          = Field(...,  description="USER.email")
  password: str                            = Field(...,  description="USER.password")
  userName: str                            = Field(...,  description="USER.name")
  agreed: bool                             = Field(...,  description="개인정보 수집 및 이용 동의 여부")

  # ── COMPANY 테이블 필드
  licensefileId: int                       = Field(...,  description="COMPANY.license_file_id")
  businessNumber: int                      = Field(...,  description="COMPANY.business_number")
  companyName: str                         = Field(...,  description="COMPANY.company_name")
  ceoName: str                             = Field(...,  description="COMPANY.ceo_name")
  openingDate: Optional[Union[str, date]]  = Field(..., description="COMPANY.company_establishment 'YYYY-MM-DD'")
  corporateNumber: Optional[int]           = Field(None,  description="COMPANY.corporate_number")
  headOffice: str                          = Field(...,  description="COMPANY.company_address")
  taxName: str                             = Field(...,  description="COMPANY.tax_name")
  issueDate: Optional[Union[str, date]]    = Field(..., description="COMPANY.issue_date 'YYYY-MM-DD'")
  companySize: Optional[str]               = Field(..., description="COMPANY.company_size")

  # ── INDUSTRY_DETAIL 테이블 필드
  # [FK] industry_id → INDUSTRY_CODE.id (배열 수신 → saveMany 일괄 INSERT)
  # [FK] company_id  → COMPANY.id       (signUpProcess 내부 주입)
  industryList: List[str]                 = Field(...,  description="INDUSTRY_DETAIL.industry_id 배열")

  # ── USER_ROLE 테이블 필드
  # [FK] role_id → ROLE.id
  roleId: int                              = Field(2,    description="USER_ROLE.role_id (기본값: 2)")

# 회원가입시 중복체크 모델
class DuplicateCheckModel(BaseModel):
    """ user.py get email,사업자 등록 번호 중복 체크 인증 모델 """
    # 이메일: 형식 검증은 EmailStr이 담당, 설명 추가
    email: Optional[EmailStr] =  Field(None, description="회원가입에서 사용되는 이메일 모델")
    # 사업자 번호: 10자리 숫자 패턴 검증 및 길이 제한, 설명 추가
    businessNumber: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",  # 숫자 10자리 정규표현식
        description="회원가입에서 사용되는 사업자 등록 번호 모델"
    )

# 회사 선택 모델
class CompanyModel(BaseModel):
   """ company.py 회사 선택 저장 """
   companyId: str = Field(..., description="회사 ID")

# 파일 업로드 모델
class FileModel(BaseModel):
    """ file.py 파일 업로드 모델 """
    file : List[UploadFile] = Field(..., description="업로드할 SR PDF 파일이름")
    fileType: str = Field(None, description="SR 파일의 유형 (Leader, Peer, Own)")
    companyName: str = Field(None, description="업로드 파일 회사 이름")
    page: str = Field(..., description="벤치마킹(SR) or 온보딩 구분(ONBOARD)")

# 파일 읽어오는 모델
class FileFindModel(BaseModel):
    """ file.py 파일 읽어오기 모델 """
    file: List[str] = Field(..., description="읽어올 SR PDF 파일이름")
    page: str = Field(..., description="벤치마킹(SR) or 온보딩 구분(ONBOARD)")

# 비번 체크 모델
class pwdCheckModel(BaseModel):
   """ auth.py patch 비밀번호 확인 모델"""
   password: str = Field(..., description="비밀번호 확인에서 사용하는 pwd 모델")

# 로그아웃 모델
class logoutModel(BaseModel):
   """ auth.py delete 로그아웃 모델"""
   uuid: str = Field(..., description="로그아웃에서 사용되는 uuid 모델")

#회원 정보 확인 모델
class userUpdateModel(BaseModel):
    """ user.py patch 회원 수정 페이지 전용 모델 (화면 항목: 새 비밀번호, 확인, 이름) """
    uuid: str = Field(..., description="회원정보 수정시 사용되는 uuid 모델")
    name: Optional[str] = Field(None, description="변경할 이름")
    newPassword: Optional[str] = Field(None, description="변경할 비밀번호")
    newPasswordConfirm: Optional[str] = Field(None, description="변경할 비밀번호 확인")

    # Pydantic 라이브러리에서 정의한 이름이라 카멜케이스 안 됨
    @model_validator(mode='after')
    def checkPasswordsMatch(self) -> 'userUpdateModel':
        # 비밀번호 변경 값이 들어온 경우에만 두 값이 일치하는지 검증
        if self.newPassword or self.newPasswordConfirm:
            if self.newPassword != self.newPasswordConfirm:
                raise ValueError("변경할 비밀번호가 서로 일치하지 않습니다.")
        return self
    
# 회원 탈퇴 모델
class userDeleteModel(BaseModel):
    """ user.py delete 회원 탈퇴 페이지 전용 모델 (uuid 이용) """
    uuid: str = Field(..., description="회원탈퇴시 사용되는 uuid 모델")
    