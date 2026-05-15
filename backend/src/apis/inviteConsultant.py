from fastapi import APIRouter
from src.models.model import inviteConsultantModel
from src.models.invite import inviteConsultantProcess

router = APIRouter()
@router.post("",
             summary="컨설턴트 초대",
             description="컨설턴트를 초대하는 API입니다. 3: 컨설턴트")
def inviteConsultant(inviteConsultantModel: inviteConsultantModel):
    return inviteConsultantProcess(inviteConsultantModel)