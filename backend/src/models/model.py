from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional, Union, List
from datetime import date
from fastapi import UploadFile

# ê³µí†µ ?‘ë‹µ ëª¨ë¸ ë°??”ì²­ ëª¨ë¸ ?•ì˜
def ResponseModel(status: bool, message: str="", data: dict={}):
    """ ?‘ë‹µ ëª¨ë¸ """
    return {
        "status": status,
        "message": message,
        "data": data
    }

# ? ì? ?•ë³´ ëª¨ë¸
class UserModel(BaseModel):
    """ auth.py ë¡œê·¸??API ëª¨ë¸ """
    uuid: str = Field(..., description="?¬ìš©???ë³„???¬ìš©?˜ëŠ” uuid")
    id: int = Field(..., description="?¬ìš©??ID")
    name: str = Field(..., description="?¬ìš©???´ë¦„")
    email: EmailStr = Field(..., description="?¬ìš©???´ë©”??)
    role: str = Field(..., description="?¬ìš©????•  ë¦¬ìŠ¤??)
    role_name: str = Field(..., description="?¬ìš©????•  ?´ë¦„ ë¦¬ìŠ¤??)

#?´ë©”??ëª¨ë¸
class EmailModel(BaseModel):
   email: EmailStr = Field(..., description="ë¹„ë?ë²ˆí˜¸ ì°¾ê¸°???¬ìš©?˜ëŠ” ?´ë©”??ëª¨ë¸")

# Company ?•ë³´ ëª¨ë¸
class SignUpModel(BaseModel):
  """user.py ?Œì›ê°€???µí•© ?”ì²­ ëª¨ë¸"""

  # ?€?€ USER ?Œì´ë¸??„ë“œ
  email: EmailStr                          = Field(...,  description="USER.email")
  password: str                            = Field(...,  description="USER.password")
  userName: str                            = Field(...,  description="USER.name")
  agreed: bool                             = Field(...,  description="ê°œì¸?•ë³´ ?˜ì§‘ ë°??´ìš© ?™ì˜ ?¬ë?")

  # ?€?€ COMPANY ?Œì´ë¸??„ë“œ
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

  # ?€?€ INDUSTRY_DETAIL ?Œì´ë¸??„ë“œ
  # [FK] industry_id ??INDUSTRY_CODE.id (ë°°ì—´ ?˜ì‹  ??saveMany ?¼ê´„ INSERT)
  # [FK] company_id  ??COMPANY.id       (signUpProcess ?´ë? ì£¼ì…)
  industryList: List[str]                 = Field(...,  description="INDUSTRY_DETAIL.industry_id ë°°ì—´")

  # ?€?€ USER_ROLE ?Œì´ë¸??„ë“œ
  # [FK] role_id ??ROLE.id
  roleId: int                              = Field(2,    description="USER_ROLE.role_id (ê¸°ë³¸ê°? 2)")

# ?Œì›ê°€?…ì‹œ ì¤‘ë³µì²´í¬ ëª¨ë¸
class DuplicateCheckModel(BaseModel):
    """ user.py get email,?¬ì—…???±ë¡ ë²ˆí˜¸ ì¤‘ë³µ ì²´í¬ ?¸ì¦ ëª¨ë¸ """
    # ?´ë©”?? ?•ì‹ ê²€ì¦ì? EmailStr???´ë‹¹, ?¤ëª… ì¶”ê?
    email: Optional[EmailStr] =  Field(None, description="?Œì›ê°€?…ì—???¬ìš©?˜ëŠ” ?´ë©”??ëª¨ë¸")
    # ?¬ì—…??ë²ˆí˜¸: 10?ë¦¬ ?«ì ?¨í„´ ê²€ì¦?ë°?ê¸¸ì´ ?œí•œ, ?¤ëª… ì¶”ê?
    businessNumber: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",  # ?«ì 10?ë¦¬ ?•ê·œ?œí˜„??        description="?Œì›ê°€?…ì—???¬ìš©?˜ëŠ” ?¬ì—…???±ë¡ ë²ˆí˜¸ ëª¨ë¸"
    )

# ?Œì‚¬ ? íƒ ëª¨ë¸
class CompanyModel(BaseModel):
   """ company.py ?Œì‚¬ ? íƒ ?€??"""
   companyId: str = Field(..., description="?Œì‚¬ ID")

# ?Œì¼ ?…ë¡œ??ëª¨ë¸
class FileModel(BaseModel):
    """ file.py ?Œì¼ ?…ë¡œ??ëª¨ë¸ """
    file : List[UploadFile] = Field(..., description="?…ë¡œ?œí•  SR PDF ?Œì¼?´ë¦„")
    fileType: str = Field(None, description="SR ?Œì¼??? í˜• (Leader, Peer, Own)")
    companyName: str = Field(None, description="?…ë¡œ???Œì¼ ?Œì‚¬ ?´ë¦„")
    page: str = Field(..., description="ë²¤ì¹˜ë§ˆí‚¹(SR) or ?¨ë³´??êµ¬ë¶„(ONBOARD)")

# ?Œì¼ ?½ì–´?¤ëŠ” ëª¨ë¸
class FileFindModel(BaseModel):
    """ file.py ?Œì¼ ?½ì–´?¤ê¸° ëª¨ë¸ """
    file: List[str] = Field(..., description="?½ì–´??SR PDF ?Œì¼?´ë¦„")
    page: str = Field(..., description="ë²¤ì¹˜ë§ˆí‚¹(SR) or ?¨ë³´??êµ¬ë¶„(ONBOARD)")

# ë¹„ë²ˆ ì²´í¬ ëª¨ë¸
class pwdCheckModel(BaseModel):
   """ auth.py patch ë¹„ë?ë²ˆí˜¸ ?•ì¸ ëª¨ë¸"""
   password: str = Field(..., description="ë¹„ë?ë²ˆí˜¸ ?•ì¸?ì„œ ?¬ìš©?˜ëŠ” pwd ëª¨ë¸")

# ë¡œê·¸?„ì›ƒ ëª¨ë¸
class logoutModel(BaseModel):
   """ auth.py delete ë¡œê·¸?„ì›ƒ ëª¨ë¸"""
   uuid: str = Field(..., description="ë¡œê·¸?„ì›ƒ?ì„œ ?¬ìš©?˜ëŠ” uuid ëª¨ë¸")

#?Œì› ?•ë³´ ?•ì¸ ëª¨ë¸
class userUpdateModel(BaseModel):
    """ user.py patch ?Œì› ?˜ì • ?˜ì´ì§€ ?„ìš© ëª¨ë¸ (?”ë©´ ??ª©: ??ë¹„ë?ë²ˆí˜¸, ?•ì¸, ?´ë¦„) """
    uuid: str = Field(..., description="?Œì›?•ë³´ ?˜ì •???¬ìš©?˜ëŠ” uuid ëª¨ë¸")
    name: Optional[str] = Field(None, description="ë³€ê²½í•  ?´ë¦„")
    newPassword: Optional[str] = Field(None, description="ë³€ê²½í•  ë¹„ë?ë²ˆí˜¸")
    newPasswordConfirm: Optional[str] = Field(None, description="ë³€ê²½í•  ë¹„ë?ë²ˆí˜¸ ?•ì¸")

    # Pydantic ?¼ì´ë¸ŒëŸ¬ë¦¬ì—???•ì˜???´ë¦„?´ë¼ ì¹´ë©œì¼€?´ìŠ¤ ????    @model_validator(mode='after')
    def checkPasswordsMatch(self) -> 'userUpdateModel':
        # ë¹„ë?ë²ˆí˜¸ ë³€ê²?ê°’ì´ ?¤ì–´??ê²½ìš°?ë§Œ ??ê°’ì´ ?¼ì¹˜?˜ëŠ”ì§€ ê²€ì¦?        if self.newPassword or self.newPasswordConfirm:
            if self.newPassword != self.newPasswordConfirm:
                raise ValueError("ë³€ê²½í•  ë¹„ë?ë²ˆí˜¸ê°€ ?œë¡œ ?¼ì¹˜?˜ì? ?ŠìŠµ?ˆë‹¤.")
        return self
    
# ?Œì› ?ˆí‡´ ëª¨ë¸
class userDeleteModel(BaseModel):
    """ user.py delete ?Œì› ?ˆí‡´ ?˜ì´ì§€ ?„ìš© ëª¨ë¸ (uuid ?´ìš©) """
    uuid: str = Field(..., description="?Œì›?ˆí‡´???¬ìš©?˜ëŠ” uuid ëª¨ë¸")
    
=======
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Union, List, Literal
