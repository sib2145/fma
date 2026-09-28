from sqlalchemy import func, select

from models.text import Text
from views.text import TextView

from jinja2 import TemplateSyntaxError

from instances.jinja import jinja_env


class TextService:

    def __init__(self, db):
        self.db = db

    async def get_next_id(self, session) -> int:
        result = await session.execute(
            select(func.max(Text.id))
        )

        max_id = result.scalar_one()

        return (max_id or 0) + 1

    async def create(
        self,
        session,
        text: str,
        locale_id: int = 1
    ) -> Text:
        text_id = await self.get_next_id(session)

        text_model = Text(
            id=text_id,
            locale_id=locale_id,
            text=text
        )

        session.add(text_model)
        await session.flush()

        return text_model

    async def update(
        self,
        text_id: int,
        text: str,
        locale_id: int = 1
    ) -> bool:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Text)
                .where(
                    Text.id == text_id,
                    Text.locale_id == locale_id
                )
            )

            text_model = result.scalar_one_or_none()

            if text_model is None:
                return False

            text_model.text = text

            await session.commit()

            return True

    def validate_template(
        self,
        template_text: str
    ):
        try:
            jinja_env.from_string(template_text)
        except TemplateSyntaxError as e:
            return False, e

        return True, None

    async def create_view(
        self,
        text: Text
    ) -> TextView:
        return TextView(
            id=text.id,
            locale_id=text.locale_id,
            template=text.text or "",
            text=text.text or "",
        )

    async def render_view(
        self,
        text_view: TextView,
        template_params: dict
    ) -> TextView:
        text_view.text = await self.render_template(
            text_view.template,
            template_params,
        )

        return text_view

    async def render_template(
        self,
        template: str,
        template_params: dict
    ) -> str:
        template = jinja_env.from_string(template)

        return template.render(
            **template_params
        )
