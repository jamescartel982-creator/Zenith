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
import http.client


def main():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='zenith-server-smoke-') as directory:
        environment = {**os.environ, 'AGENT_DATA_DIR': directory, 'AI_PROVIDER': 'huggingface',
                       'ZENITH_API_TOKEN': '', 'ZENITH_ALLOWED_HOSTS': 'localhost,127.0.0.1,::1'}
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
                def request(method, path, body=None, headers=None, chunked=False):
                    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                    try:
                        connection.request(method, path, body=body, headers=headers or {}, encode_chunked=chunked)
                        response = connection.getresponse()
                        return response.status, response.read()
                    finally:
                        connection.close()
                assert request('GET', '/api/account', headers={'Host': 'attacker.example'})[0] == 400
                assert request('GET', '/api/account', headers={'Sec-Fetch-Site': 'cross-site'})[0] == 403
                password = 'private-invalid-password-' * 20
                status, data = request('POST', '/api/account/login', json.dumps({'username': 'alice', 'password': password}), {'Content-Type': 'application/json'})
                assert status == 422 and password.encode() not in data
                chunks = iter([b'x' * (256*1024), b'x' * (256*1024), b'x'])
                assert request('POST', '/api/account/login', chunks, {'Content-Type': 'application/json'}, chunked=True)[0] == 413
                print('Real local server startup, health, UI, Host, cross-site, redaction and chunked-body checks passed.')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)


if __name__ == '__main__':
    main()
