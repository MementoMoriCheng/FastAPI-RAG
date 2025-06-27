from tortoise import fields

from app.models import BaseModel


class UserLlm(BaseModel):
    """
    用户 LLM 配置模型
    对应数据库表名：user_llm
    """
    user_id = fields.BigIntField(description="用户 ID")
    llm_name = fields.CharField(max_length=50, description="LLM 名称")
    model_type = fields.CharField(max_length=50, description="模型类型 (LLM/文本嵌入/图文生成/语音识别)", null=True)
    max_tokens = fields.IntField(default=512, description="最大 token 数", null=True)
    status = fields.IntField(default=1, description="是否有效 (0: 废弃, 1: 有效)", null=True)
    api_key = fields.TextField(description="LLM API 密钥")  # 推荐使用 TextField 存储长字符串
    api_base = fields.TextField(description="LLM API 地址")

    def __str__(self):
        return f"<UserLlm(user_id='{self.user_id}', llm_name='{self.llm_name}', model_type='{self.model_type}')>"

    class Meta:
        table = "user_llm"  # 数据库表名
