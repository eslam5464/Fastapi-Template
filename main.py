import uvicorn
from app.core.config import settings


def main():
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.reload_uvicorn,
        workers=settings.workers_count,
    )


if __name__ == "__main__":
    main()
