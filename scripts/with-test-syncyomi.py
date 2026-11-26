"""Run the Android tests against a disposable, loopback-only SyncYomi v2 server."""

import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.error import URLError
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request, urlopen


def binary(directory):
    local = os.environ.get("MIHON_TEST_SYNCYOMI_BINARY")
    if local:
        return Path(local).resolve(strict=True)
    archive = directory / "syncyomi.tar.gz"
    url = "https://github.com/SyncYomi/SyncYomi/releases/download/v1.7.4/syncyomi_1.7.4_linux_x86_64.tar.gz"
    with urlopen(url, timeout=60) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != "1dc4b3d8c81f934b07fb432f7f56805589db6eaddb941945bf9ba90c8644fd9f":
            raise RuntimeError("Unexpected SyncYomi test release digest")
    target = directory / "syncyomi"
    with tarfile.open(archive) as tar:
        member, = [m for m in tar if m.isfile() and Path(m.name).name == "syncyomi"]
        with tar.extractfile(member) as stream, target.open("wb") as output:
            shutil.copyfileobj(stream, output)
    target.chmod(0o700)
    return target


def run(command):
    with tempfile.TemporaryDirectory(prefix="mihon-sync-test-") as temp:
        directory = Path(temp)
        server = binary(directory)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (directory / "config.toml").write_text(f'host = "127.0.0.1"\nport = {port}\n')
        base = f"http://127.0.0.1:{port}"
        client = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def post(path, data):
            req = Request(base + "/api/" + path, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
            with client.open(req, timeout=5) as response:
                return response.read()

        process = subprocess.Popen(
            [server, "--config", directory], cwd=directory, env={"PATH": os.defpath},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("SyncYomi fixture exited before it was ready")
                try:
                    with client.open(base + "/api/healthz/readiness", timeout=1):
                        break
                except URLError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Local SyncYomi fixture did not become ready")
            user = {"username": "integration", "password": secrets.token_urlsafe(24)}
            post("auth/onboard", user)
            post("auth/login", user)
            key = json.loads(post("keys", {"name": "manga-round-trip", "scopes": ["sync"]}))["key"]
            env = dict(os.environ, MIHON_TEST_SYNCYOMI_URL=base, MIHON_TEST_SYNCYOMI_KEY=key)
            return subprocess.call(command, env=env)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
