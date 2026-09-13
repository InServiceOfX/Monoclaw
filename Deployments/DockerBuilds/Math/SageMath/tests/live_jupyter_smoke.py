"""Explicit Docker integration smoke: ephemeral Jupyter, auth check, clean stop.

Run directly; not part of offline unittest discovery. Never prints tokens.
"""
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener


def main():
    launcher = Path(__file__).resolve().parents[1] / 'sage.py'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    opener = build_opener(ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='sage-jupyter-smoke-') as scratch:
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen([sys.executable, '-B', str(launcher),
                '--workdir', scratch, '--write', '--port', str(port), 'jupyter'],
                stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 45
                authenticated = False
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise AssertionError('Jupyter exited before becoming ready')
                    try:
                        with opener.open(f'http://127.0.0.1:{port}/api/sessions', timeout=1) as response:
                            raise AssertionError(f'Unauthenticated API access returned {response.status}')
                    except HTTPError as exc:
                        assert exc.code == 403, exc.code
                        authenticated = True
                        break
                    except (URLError, OSError):
                        time.sleep(0.25)
                assert authenticated, 'Jupyter did not become ready within 45 seconds'
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=25)
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(('127.0.0.1', port)) != 0, 'Jupyter port remained open'
    print('PASS: unauthenticated API returns 403; session stopped; token not logged')


if __name__ == '__main__':
    main()
