"""Open local browser chat only after this server starts accepting connections."""
import time
import webbrowser


def open_when_ready(server, url, stopped, timeout=60):
    deadline = time.monotonic() + timeout
    while not stopped.is_set() and time.monotonic() < deadline:
        if server.started:
            try:
                if webbrowser.open(url):
                    return
            except (OSError, webbrowser.Error):
                pass
            print('Open Zenith in your browser: ' + url, flush=True)
            return
        if stopped.wait(0.1):
            return
    if not stopped.is_set():
        print('When the server is ready, open: ' + url, flush=True)
