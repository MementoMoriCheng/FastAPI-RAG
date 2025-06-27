from tortoise import fields
from app.models import BaseModel

class KnowledgeFile(BaseModel):
    file_name = fields.CharField(max_length=255, description="文件名")
    file_ext = fields.CharField(max_length=10, description="文件类型")
    kb_name = fields.CharField(max_length=50, description="所属知识库名称")
    document_loader_name = fields.CharField(max_length=50, description="文档加载器名称", null=True)
    text_splitter_name = fields.CharField(max_length=50, description="文本分割器名称", null=True)
    file_size = fields.IntField(default=0, description="文件大小")
    docs_count = fields.IntField(default=0, description="切分文档数量")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")

    def __str__(self):
        return f"<KnowledgeFile(id='{self.id}', file_name='{self.file_name}', kb_name='{self.kb_name}')>"

    class Meta:
        table = "knowledge_file"


class FileDoc(BaseModel):
    kb_name = fields.CharField(max_length=50, description="知识库名称")
    file_name = fields.CharField(max_length=255, description="文件名称")
    doc_id = fields.CharField(max_length=50, description="向量库文档ID")
    meta_data = fields.JSONField(default=dict, description="元数据")

    def __str__(self):
        return f"<FileDoc(id='{self.id}', kb_name='{self.kb_name}', file_name='{self.file_name}', doc_id='{self.doc_id}')>"

    class Meta:
        table = "file_doc"