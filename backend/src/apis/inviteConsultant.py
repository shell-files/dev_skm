<<<<<<< HEAD
"""
inviteConsultant.py
레이어: API Router
역할: 컨설턴트 초대 엔드포인트.

엔드포인트:
  POST /  — 컨설턴트 초대 (role: 3)
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter, Depends
from src.models.model import inviteConsultantModel
from src.utils.invite import inviteConsultantProcess
from src.utils.auth import get_token


router = APIRouter()
<<<<<<< HEAD


=======
>>>>>>> origin/skm_test
@router.post("",
             summary="컨설턴트 초대",
             description="컨설턴트를 초대하는 API입니다. 3: 컨설턴트")
def inviteConsultant(inviteConsultantModel: inviteConsultantModel, userModel = Depends(get_token)):
<<<<<<< HEAD
    return inviteConsultantProcess(inviteConsultantModel, userModel)
=======
    
    return inviteConsultantProcess(inviteConsultantModel, userModel)
>>>>>>> origin/skm_test
