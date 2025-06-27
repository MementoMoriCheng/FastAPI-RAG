import logging
from http.client import HTTPException

from fastapi import APIRouter, Query

from app.controllers.user_llm import user_llm_controller
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.user_llm import *

# logger = logging.getLogger(__name__)

user_llm_router = APIRouter(prefix="/user_llm")


@user_llm_router.get("/get", summary="查看用户模型配置")
async def get_user_llm(
    user_id: int = Query(..., description="用户ID"),
):
    user_llm_obj = await user_llm_controller.get(id=user_id)
    return Success(data=await user_llm_obj.to_dict())


@user_llm_router.post("/create", summary="创建用户模型配置")
async def create_user_llm(user_llm: UserLlmCreate):
    if await user_llm_controller.is_exist(api_key=user_llm.api_key):
        raise HTTPException(
            status_code=400,
            detail="The api key already exists in the system.",
        )
    await user_llm_controller.create(obj_in=user_llm)
    return Success(msg="Created Successfully")


# @router.post("/update", summary="更新用户模型配置")
# async def update_user_llm(user_llm_in: UserLlmUpdate):
#     await user_llm_controller.update(id=user_llm_in.id, obj_in=user_llm_in)
#     return Success(msg="Updated Successfully")


@user_llm_router.delete("/delete", summary="删除用户模型配置")
async def delete_user_llm(
    user_id: int = Query(..., description="用户ID"),
):
    await user_llm_controller.remove(id=user_id)
    return Success(msg="Deleted Success")