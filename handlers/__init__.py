from .start import router as start_router
from .language import router as language_router
from .wallet import router as wallet_router
# play_router временно отключён из Start потока
from .play import router as play_router

all_handlers_routers = [
    start_router,
    language_router,
    wallet_router,
    play_router
]
