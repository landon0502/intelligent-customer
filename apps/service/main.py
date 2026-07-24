import uvicorn
from app.core.config import settings


def start():
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    start()