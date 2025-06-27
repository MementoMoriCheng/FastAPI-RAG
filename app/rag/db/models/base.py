from tortoise import fields, models


# ========== BaseModel 定义 ==========
class BaseModel(models.Model):
    id = fields.CharField(pk=True, description="主键ID")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")
    create_by = fields.CharField(max_length=255, null=True, description="创建者")
    update_by = fields.CharField(max_length=255, null=True, description="更新者")

    class Meta:
        abstract = True
