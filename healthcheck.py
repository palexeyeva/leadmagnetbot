from threading import Thread
from aiohttp import web

async def handle(request):
    return web.Response(text="OK")

def start_healthcheck_server():
    """
    Запускает aiohttp-сервер на 0.0.0.0:8000 в отдельном потоке.
    """
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    web.run_app(app, host="0.0.0.0", port=8000)

def run():
    t = Thread(target=start_healthcheck_server, daemon=True)
    t.start()
