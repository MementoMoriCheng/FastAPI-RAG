from typing import List, Optional
from app.core.crud import CRUDBase
from app.rag.db.models.knowledge_base_model import KnowledgeBase
from app.schemas.kb import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KBController(CRUDBase[KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate]):
    def __init__(self):
        super().__init__(model=KnowledgeBase)

    async def is_exist(self, name: str) -> bool:
        return await self.model.filter(kb_name=name).exists()


kb_controller = KBController()
