from tortoise import fields

from app.models import BaseModel


class KnowledgeBase(BaseModel):
    permission_id = fields.IntField(description="权限管理（按人员/部门）")
    kb_name = fields.CharField(max_length=50, description="知识库名称")
    kb_info = fields.TextField(description="知识库简介", null=True)
    vs_type = fields.CharField(max_length=50, description="向量库类型", null=True)
    embed_model = fields.CharField(max_length=50, description="嵌入模型名称", null=True)
    file_count = fields.IntField(default=0, description="文件数量", null=True)
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")

    def __str__(self):
        return f"<KnowledgeBase(id='{self.id}', kb_name='{self.kb_name}')>"

    class Meta:
        table = "knowledge_base"
