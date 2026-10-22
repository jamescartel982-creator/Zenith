"""Start the real local web server, check its API, and shut it down."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import json


def main():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='zenith-server-smoke-') as directory:
        environment = {**os.environ, 'AGENT_DATA_DIR': directory, 'AI_PROVIDER': 'huggingface'}
        with tempfile.TemporaryFile(mode='w+b') as log:
            process = subprocess.Popen([sys.executable, '-m', 'agent', 'serve', '--port', str(port)],
                                       env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('Server exited during startup')
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/healthz', timeout=1) as response:
                            health = json.load(response)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Server startup timed out')
                assert health['status'] == 'ok'
                with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                    assert b'Message Zenith' in response.read()
                print('Real local server startup, health and UI checks passed.')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)


if __name__ == '__main__':
    main()
