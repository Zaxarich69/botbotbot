from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker[AsyncSession]):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Open a scoped AsyncSession for this update
        async with self.session_pool() as session:
            # Use specific keys to avoid collisions and expose the factory for background tasks
            data["db_session"] = session
            data["db_session_factory"] = self.session_pool

            # Use a transactional scope; it will commit on success and roll back on exception
            async with session.begin():
                try:
                    result = await handler(event, data)
                    return result
                except BaseException:
                    # session.begin() will roll back automatically; re-raise to preserve cancellation/errors
                    raise
                finally:
                    # Cleanup keys to prevent accidental reuse outside this scope
                    data.pop("db_session", None)
                    data.pop("db_session_factory", None)
