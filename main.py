import os
import sys

import anyio
import uvicorn
from anyio.to_thread import current_default_thread_limiter

from app.core.config import settings


async def monitor_thread_limiter():
    limiter = current_default_thread_limiter()
    threads_in_use = limiter.borrowed_tokens
    while True:
        if threads_in_use != limiter.borrowed_tokens:
            print(f"Threads in use: {limiter.borrowed_tokens}")
            threads_in_use = limiter.borrowed_tokens
        await anyio.sleep(0)


def main():
    is_linux = sys.platform.startswith("linux")

    if settings.debug:
        os.environ["PYTHONASYNCIODEBUG"] = "1"
        config = uvicorn.Config(
            app="app.main:app",
            host=settings.backend_host,
            port=settings.backend_port,
            reload=settings.reload_uvicorn,
            workers=settings.workers_count,
            loop="uvloop",
        )
        server = uvicorn.Server(config)

        async def main_monitor():
            async with anyio.create_task_group() as tg:
                tg.start_soon(monitor_thread_limiter)
                await server.serve()

        anyio.run(main_monitor)
    else:
        if is_linux:
            from app.web import GunicornApplication

            options = {
                "bind": f"{settings.backend_host}:{settings.backend_port}",
                "workers": settings.workers_count,
                "worker_class": "uvicorn.workers.UvicornWorker",
            }
            GunicornApplication("app.main:app", options).run()
        else:
            uvicorn.run(
                app="app.main:app",
                host=settings.backend_host,
                port=settings.backend_port,
                reload=settings.reload_uvicorn,
                workers=settings.workers_count,
            )


if __name__ == "__main__":
    main()
