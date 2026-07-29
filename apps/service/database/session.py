from .mysql import async_session_factory


async def get_db():
    async with async_session_factory() as session:
        yield session