from typing import List, Optional
from app.core.crud import CRUDBase
from app.rag.db.models.user_llm_model import UserLlm
from app.schemas.user_llm import UserLlmCreate, UserLlmUpdate


class UserLlmController(CRUDBase[UserLlm, UserLlmCreate, UserLlmUpdate]):
    def __init__(self):
        super().__init__(model=UserLlm)

    async def is_exist(self, api_key: str) -> bool:
        return await self.model.filter(api_key=api_key).exists()

    # async def get(self, email: str) -> Optional[UserLlm]:
    #     return await self.model.filter(email=email).first()

    # async def update_roles(self, role: Role, menu_ids: List[int], api_infos: List[dict]) -> None:
    #     await role.menus.clear()
    #     for menu_id in menu_ids:
    #         menu_obj = await Menu.filter(id=menu_id).first()
    #         await role.menus.add(menu_obj)
    #
    #     await role.apis.clear()
    #     for item in api_infos:
    #         api_obj = await Api.filter(path=item.get("path"), method=item.get("method")).first()
    #         await role.apis.add(api_obj)


user_llm_controller = UserLlmController()
