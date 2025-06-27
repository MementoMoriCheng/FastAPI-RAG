import logging
from typing import List, Literal
from fastapi.responses import JSONResponse
from app.schemas.base import Fail, Success
from fastapi import APIRouter
from fastapi import UploadFile

#
# # logger = logging.getLogger(__name__)
#
file_router = APIRouter(prefix="/file")


@file_router.post("/upload_and_parse", summary="上传文件到知识库，并进行向量化")
async def upload_docs(
    files: List[UploadFile],
    # kb_name: str = Form(..., example="samples"),
):
    if len(files) == 0:
        return Fail(msg="No file part!")
    # 获取文件名列表（安全处理）
    file_names = [f.filename for f in files]
    file_objs = [f for f in files]
    print(file_names)
    print(file_objs)

    # # 业务逻辑处理（例如保存文件、向量化）
    # return JSONResponse(
    #     status_code=200,
    #     content={
    #         "message": "文件上传成功",
    #         "details": {"filenames": [file.filename for file in files]}
    #     }
    # )