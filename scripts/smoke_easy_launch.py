"""Check actual browser-ready startup without opening a desktop browser."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def main():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='zenith easy launch ') as folder:
        marker = Path(folder) / 'browser-open.json'
        code = '''
import json,os,sys,webbrowser
from urllib.request import urlopen
class Browser:
    def open(self,url,new=0,autoraise=True):
        with urlopen(url+'/healthz',timeout=5) as response:
            assert json.load(response)['status']=='ok'
        with open(os.environ['ZENITH_TEST_BROWSER_MARKER'],'w') as handle:
            json.dump({'url':url,'healthy_before_open':True},handle)
        return True
webbrowser.register('zenith-test',None,Browser(),preferred=True)
from agent.commands import main
raise SystemExit(main(['serve','--open-browser','--port',sys.argv[1]]))
'''
        environment = {**os.environ, 'AI_PROVIDER':'ollama', 'ZENITH_HOME':folder,
                       'AGENT_DATA_DIR':str(Path(folder)/'data'), 'ZENITH_TEST_BROWSER_MARKER':str(marker)}
        with tempfile.TemporaryFile(mode='w+b') as log:
            process = subprocess.Popen([sys.executable,'-c',code,str(port)],env=environment,stdout=log,stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 40
                while not marker.exists():
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError('Easy launch exited: '+log.read().decode('utf-8',errors='replace'))
                    if time.monotonic() > deadline:
                        raise RuntimeError('Browser-ready startup timed out')
                    time.sleep(0.1)
                # The marker is tiny and is written once; wait for writer close.
                for attempt in range(10):
                    try:
                        result = json.loads(marker.read_text())
                        break
                    except json.JSONDecodeError:
                        time.sleep(0.05)
                else:
                    raise RuntimeError('Browser marker was incomplete')
                assert result == {'url':f'http://127.0.0.1:{port}','healthy_before_open':True}
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
    print('Easy launch opened the browser URL only after its local server was healthy.')


if __name__ == '__main__':
    main()
