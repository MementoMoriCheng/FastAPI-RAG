import json
import logging
from typing import List, Literal
from tortoise.expressions import Q
from http.client import HTTPException
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from fastapi import Body, File, Form, Query, UploadFile
from app.controllers.kb import kb_controller
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.kb import *

#
# # logger = logging.getLogger(__name__)
#
knowledge_base_router = APIRouter(prefix="/knowledge_base")


@knowledge_base_router.get("/list_knowledge_bases", summary="获取知识库列表")
async def list_kb(
        page: int = Query(1, description="页码"),
        page_size: int = Query(10, description="每页数量"),
        kb_name: str = Query("", description="名称，用于查询"),
):
    q = Q()
    if kb_name:
        q = Q(kb_name__contains=kb_name)
    total, role_objs = await kb_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict() for obj in role_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@knowledge_base_router.get("/get", summary="获取知识库信息")
async def get_kb_detail(
        kb_id: int = Query(..., description="知识库 ID"),
):
    kb_obj = await kb_controller.get(id=kb_id)
    return Success(data=await kb_obj.to_dict())


@knowledge_base_router.post("/create", summary="创建知识库")
async def create_kb(kb: KnowledgeBaseCreate):
    if await kb_controller.is_exist(name=kb.kb_name):
        raise HTTPException(
            status_code=400,
            detail="知识库已存在",
        )
    await kb_controller.create(obj_in=kb)
    return Success(msg="Created Successfully")


@knowledge_base_router.post("/update", summary="更新知识库")
async def update_kb(kb_in: KnowledgeBaseUpdate):
    await kb_controller.update(id=kb_in.id, obj_in=kb_in)
    return Success(msg="Updated Successfully")


@knowledge_base_router.delete("/delete", summary="删除知识库")
async def delete_kb(
        kb_id: int = Query(..., description="知识库 ID"),
):
    await kb_controller.remove(id=kb_id)
    return Success(msg="Deleted Success")


# ********************文档接口*********************

@knowledge_base_router.post("/upload_and_parse", summary="上传文件到知识库，并进行向量化")
def upload_docs(
        files: List[UploadFile] = File(..., description="上传文件，支持多文件"),
        knowledge_base_name: str = Form(
            ..., description="知识库名称"),
        # override: bool = Form(False, description="覆盖已有文件"),
        # to_vector_store: bool = Form(True, description="上传文件后是否进行向量化"),
        # chunk_size: int = Form(Settings.kb_settings.CHUNK_SIZE, description="知识库中单段文本最大长度"),
        # chunk_overlap: int = Form(Settings.kb_settings.OVERLAP_SIZE, description="知识库中相邻文本重合长度"),
        # zh_title_enhance: bool = Form(Settings.kb_settings.ZH_TITLE_ENHANCE, description="是否开启中文标题加强"),
        # docs: str = Form("", description="自定义的docs，需要转为json字符串"),
        # not_refresh_vs_cache: bool = Form(False, description="暂不保存向量库（用于FAISS）"),
):
    #     """
    #     API接口：上传文件，并/或向量化
    #     """
    # if not validate_kb_name(knowledge_base_name):
    #     return BaseResponse(code=403, msg="Don't attack me")
    #
    # kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    # if kb is None:
    #     return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")

    # docs = json.loads(docs) if docs else {}
    # failed_files = {}
    # file_names = list(docs.keys())

    # TODO 先将上传的文件保存到Minio

    # for result in _save_files_in_thread(
    #         files, knowledge_base_name=knowledge_base_name, override=override
    # ):
    #     filename = result["data"]["file_name"]
    #     if result["code"] != 200:
    #         failed_files[filename] = result["msg"]
    #
    #     if filename not in file_names:
    #         file_names.append(filename)

    # TODo 对保存的文件进行向量化
    # if to_vector_store:
    #     result = update_docs(
    #         knowledge_base_name=knowledge_base_name,
    #         file_names=file_names,
    #         override_custom_docs=True,
    #         chunk_size=chunk_size,
    #         chunk_overlap=chunk_overlap,
    #         zh_title_enhance=zh_title_enhance,
    #         docs=docs,
    #         not_refresh_vs_cache=True,
    #     )
    #     failed_files.update(result.data["failed_files"])
    #     if not not_refresh_vs_cache:
    #         kb.save_vector_store()
    if len(files) == 0:
        return Fail(msg="No file part!")
    # 获取文件名列表（安全处理）
    file_objs = [f for f in files]
    print(file_objs)

    file_names = [f.filename for f in files]
    print(f"收到 {len(file_names)} 个文件：{file_names}")
    print(f"目标知识库：{knowledge_base_name}")

    return Success(msg="文件上传与向量化完成")
