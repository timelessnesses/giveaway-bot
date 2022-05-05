import typing

import asyncpg


class EasySQL:
    def __init__(self) -> None:
        self.db = None
        self.cursor = None

    async def connect(
        self, host, database, user, password
    ) -> typing.Optional[asyncpg.connection.Connection]:
        self.db = await asyncpg.connect(
            host=host, database=database, user=user, password=password
        )
        self.cursor = self.db.cursor
        return self.db

    async def execute(
        self, query, *args
    ) -> typing.Optional[asyncpg.connection.Connection]:
        return await self.cursor.execute(query, *args)

    async def fetch(
        self, query, *args
    ) -> typing.Optional[asyncpg.connection.Connection]:
        return dict(await self.cursor.fetch(query, *args))

    async def close(self) -> None:
        await self.cursor.close()
        await self.db.close()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def __aenter__(self) -> "EasySQL":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
