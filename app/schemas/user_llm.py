from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# class BaseUserLlm(BaseModel):
#     user_id: int
#     llm_name: str
#     model_type: str = ""
#     api_key: str = ""
#     api_base: str = ""
#     max_tokens: int = ""
#     create_time: Optional[datetime]
#     update_time: Optional[datetime]


class UserLlmCreate(BaseModel):
    user_id: int = Field(example="用户id")
    llm_name: str = Field(example="模型名称")
    model_type: str = Field("", example="模型类型")
    api_key: str = Field("", example="API密钥")
    api_base: str = Field("", example="API地址")


class UserLlmUpdate(BaseModel):
    llm_name: str = Field(example="模型名称")
    model_type: str = Field("", example="模型类型")
    api_key: str = Field("", example="API密钥")
    api_base: str = Field("", example="API地址")
