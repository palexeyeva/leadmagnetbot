# healthcheck.py
from threading import Thread
from aiohttp import web
import os


async def handle(request):
    return web.Response(text="OK")


def start_healthcheck_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])

    port = int(os.getenv("PORT", "8000"))
    web.run_app(app, host="0.0.0.0", port=port, handle_signals=False)


def run():
    t = Thread(target=start_healthcheck_server, daemon=True)
    t.start()
