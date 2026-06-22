"""
model.py
레이어: Model
역할: 공통 응답 모델 및 인증·회원·초대 관련 Pydantic 요청 모델 정의.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional, Union, List
from datetime import date
from fastapi import UploadFile

def ResponseModel(status: bool, message: str="", data: dict={}):
    """ 응답 모델 """
    return {
        "status": status,
        "message": message,
        "data": data
    }

class UserModel(BaseModel):
    """ auth.py 로그인 API 모델 """
    uuid: str = Field(..., description="사용자 식별에 사용되는 uuid")
    id: int = Field(..., description="사용자 ID")
    name: str = Field(..., description="사용자 이름")
    email: EmailStr = Field(..., description="사용자 이메일")
    role: str = Field(..., description="사용자 역할 리스트")
    role_name: str = Field(..., description="사용자 역할 이름 리스트")

class EmailModel(BaseModel):
   email: EmailStr = Field(..., description="비밀번호 찾기에 사용되는 이메일 모델")

class LoginModel(BaseModel):
  """ auth.py post 로그인 모델 """
  email: EmailStr = Field(..., description="로그인에서 사용되는 이메일 모델")
  password: str = Field(..., description="로그인에서 사용하는 pwd 모델")

class SignUpModel(BaseModel):
  """user.py 회원가입 통합 요청 모델"""

  email: EmailStr                          = Field(...,  description="USER.email")
  password: str                            = Field(...,  description="USER.password")
  userName: str                            = Field(...,  description="USER.name")
  agreed: bool                             = Field(...,  description="개인정보 수집 및 이용 동의 여부")

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

  # [FK] industry_id → INDUSTRY_CODE.id (배열 수신 → saveMany 일괄 INSERT)
  # [FK] company_id  → COMPANY.id       (signUpProcess 내부 주입)
  industryList: List[str]                 = Field(...,  description="INDUSTRY_DETAIL.industry_id 배열")

  # [FK] role_id → ROLE.id
  roleId: int                              = Field(2,    description="USER_ROLE.role_id (기본값: 2)")

class DuplicateCheckModel(BaseModel):
    """ user.py get email,사업자 등록 번호 중복 체크 인증 모델 """
    email: Optional[EmailStr] =  Field(None, description="회원가입에서 사용되는 이메일 모델")
    businessNumber: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="회원가입에서 사용되는 사업자 등록 번호 모델"
    )

class CompanyModel(BaseModel):
   """ company.py 회사 선택 저장 """
   companyId: str = Field(..., description="회사 ID")

class pwdCheckModel(BaseModel):
   """ auth.py patch 비밀번호 확인 모델"""
   password: str = Field(..., description="비밀번호 확인에서 사용하는 pwd 모델")

class logoutModel(BaseModel):
   """ auth.py delete 로그아웃 모델"""
   uuid: str = Field(..., description="로그아웃에서 사용되는 uuid 모델")

class userUpdateModel(BaseModel):
    """ user.py patch 회원 수정 페이지 전용 모델 (화면 항목: 새 비밀번호, 확인, 이름) """
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
class userDeleteModel(BaseModel):
    """ user.py delete 회원 탈퇴 페이지 전용 모델 (uuid 이용) """
    uuid: str = Field(..., description="회원탈퇴시 사용되는 uuid 모델")


class inviteMemberModel(BaseModel):
    """ inviteMember.py 내부 직원 초대 API 모델 """
    email: List[EmailStr] = Field(..., description="초대할 내부 직원의 이메일")
    issue: List[int]= Field(..., description="이슈 그룹 리스트")
    role: int = Field(..., description="권한 모델(Consultant, Employee)")

class inviteConsultantModel(BaseModel):
    """컨설턴트 초대 API 모델"""
    email: List[EmailStr] = Field(..., description="초대할 컨설턴트 이메일")
    role: int = Field(..., description="권한 (3)")

class inviteSignUpUserInfo(BaseModel):
  """ invite.py 초대 링크로 회원가입 API 모델 """
  companyName: str = Field(..., description="초대 링크로 회원가입 시 사용되는 회사명")
  email: EmailStr = Field(..., description="초대 링크로 회원가입 시 사용되는 이메일")
  name: str = Field(..., description="초대 링크로 회원가입 시 사용되는 이름")
  password: str = Field(..., description="초대 링크로 회원가입 시 사용되는 비밀번호")
