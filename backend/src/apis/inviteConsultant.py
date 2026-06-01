from fastapi import APIRouter, Depends
from src.models.model import inviteConsultantModel
from src.utils.invite import inviteConsultantProcess
from src.utils.auth import get_token


router = APIRouter()
@router.post("",
             summary="컨설턴트 초대",
             description="컨설턴트를 초대하는 API입니다. 3: 컨설턴트")
def inviteConsultant(inviteConsultantModel: inviteConsultantModel, userModel = Depends(get_token)):
    return inviteConsultantProcess(inviteConsultantModel, userModel)