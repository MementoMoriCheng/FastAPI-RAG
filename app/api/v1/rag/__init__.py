from fastapi import APIRouter
from .user_llm import user_llm_router
from .knowledge_base import knowledge_base_router
# from .file import file_router

main_router = APIRouter()

main_router.include_router(user_llm_router, tags=["用户模型配置"])
main_router.include_router(knowledge_base_router, tags=["知识库管理"])
# main_router.include_router(file_router, tags=["文件管理"])

__all__ = ["main_router"]
