"""Start the dashboard and open it in a new browser window: python -m dashboard"""

import threading
import webbrowser

import uvicorn

from dashboard.config import Settings


def main() -> None:
    settings = Settings.from_env()
    url = f"http://{settings.host}:{settings.port}"
    if problem := settings.agent_problem():
        print(f"Warning: {problem}")
    threading.Timer(1.2, lambda: webbrowser.open_new(url)).start()
    print(f"Dashboard running at {url} (Ctrl+C to stop). Agent project: {settings.agent_dir}")
    uvicorn.run("dashboard.app:app", host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()
