"""Start Clarity and open the browser after the server is ready."""
import threading
import webbrowser

import uvicorn


HOST = '127.0.0.1'
PORT = 8000
URL = f'http://{HOST}:{PORT}'


class BrowserServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        if self.started:
            threading.Thread(target=webbrowser.open, args=(URL,), daemon=True).start()


if __name__ == '__main__':
    print(f'Clarity opens at {URL}. Keep this window open while using it.', flush=True)
    BrowserServer(uvicorn.Config('app:app', host=HOST, port=PORT)).run()
