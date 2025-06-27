import asyncio
from tortoise import Tortoise

async def init_db():
    await Tortoise.init(
        db_url='mysql://root:123456@localhost/langchain_rag',
        modules={'models': ['app.rag.db.models']}  # 如果模型在其他模块中，请替换路径
    )
    await Tortoise.generate_schemas()
    print("✅ 表已成功创建！")

if __name__ == "__main__":
    asyncio.run(init_db())

    # create_tables()
