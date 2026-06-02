from pydantic import BaseModel, Field, ConfigDict
from fastapi import UploadFile
from typing import List, Literal, Optional

# 파일 업로드 모델
class FileModel(BaseModel):
    """ file.py 파일 업로드 모델 (벤치마크용) """
    file : List[UploadFile] = Field(..., description="업로드할 SR PDF 파일이름")
    fileType: str = Field(None, description="SR 파일의 유형 (Leader, Peer, Own)")
    companyName: str = Field(None, description="업로드 파일 회사 이름")
    page: str = Field(..., description="벤치마킹(SR) or 온보딩 구분(ONBOARD)")

# 파일 읽어오는 모델
class FileFindModel(BaseModel):
    """ file.py 파일 읽어오기 모델 (벤치마크용) """
    model_config = ConfigDict(populate_by_name=True)
    file: List[str] = Field(..., description="읽어올 SR PDF 파일이름")
    page: str = Field(..., description="벤치마킹(SR) or 온보딩 구분(ONBOARD)")
    esgMaterialityRunId: int = Field(1, description="ESG Materiality Run ID", alias="esg_materiality_run_id")
    sourceStep: Literal["benchmark", "media_external", "survey"] = Field("benchmark", description="Source Step", alias="source_step")
    sourceType: Optional[str] = Field(None, description="Source Type (예: leader_sr, peer_sr, own_sr, news, regulation)", alias="source_type")
