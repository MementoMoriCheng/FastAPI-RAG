from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KnowledgeBase(BaseModel):
    id: int
    permission_id: int = None
    kb_name: str
    kb_info: Optional[str] = None
    vs_type: Optional[str] = None
    embed_model: Optional[str] = None
    file_count: Optional[int] = 0
    create_time: Optional[datetime] = None


class KnowledgeBaseCreate(BaseModel):
    id: int = Field(example="用户id")
    permission_id: int = Field(example="权限控制")
    kb_name: str = Field(example="知识库名称")
    kb_info: str = Field(example="知识库信息")
    vs_type: str = Field(example="向量库类型")
    embed_model: str = Field(example="嵌入模型")
    file_count: int = Field(example="文档数")


class KnowledgeBaseUpdate(BaseModel):
    id: int = Field(example="用户id")
    permission_id: int = Field(example="权限控制")
    kb_info: str = Field(example="知识库信息")
    vs_type: str = Field(example="向量库类型")
    embed_model: str = Field(example="嵌入模型")
