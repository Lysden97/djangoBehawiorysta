"""Exercise production proxy DNS recovery and static cache headers in an isolated Docker network."""

import argparse
import json
import re
import ssl
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
BACKEND = """
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode()
        payload = json.dumps(dict(backend=sys.argv[1], path=self.path, body=body,
                                  method=self.command, host=self.headers.get('Host'),
                                  proto=self.headers.get('X-Forwarded-Proto'))).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_POST = do_GET

HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
"""


def docker(*args):
    completed = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=60, check=True
    )
    return completed.stdout.strip()


def check_security_headers(headers):
    expected = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    for name, value in expected.items():
        assert headers.get_all(name) == [value], headers


def wait_for_backend(url, context, expected, timeout=30):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            request = Request(url + "/probe?value=a%2Fb", headers={"Host": "example.test"})
            with urlopen(request, context=context, timeout=2) as response:
                check_security_headers(response.headers)
                payload = json.load(response)
            if payload["backend"] == expected:
                assert payload["path"] == "/probe?value=a%2Fb", payload
                assert payload["host"] == "example.test", payload
                assert payload["proto"] == "https", payload
                return
            last_error = payload
        except (URLError, TimeoutError, OSError) as error:
            last_error = error
        time.sleep(0.5)
    raise AssertionError(f"Proxy did not reach {expected} within {timeout}s: {last_error}")


def prepare_static_files(backend, staging):
    """Collect real assets with the production storage, without contacting external services."""
    script = """
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'djangoBehawiorysta.test_settings'
import django
django.setup()
import json
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import override_settings
from website.test_staticfiles import application_settings
with override_settings(DEBUG=False, STATIC_ROOT='/tmp/static-cache',
                       STORAGES=application_settings(False)['STORAGES']):
    call_command('collectstatic', interactive=False, verbosity=0)
    print(json.dumps([staticfiles_storage.url(name) for name in
                     ('website/css/site.css', 'website/js/site.js',
                      'website/webfonts/fa-solid-900.woff2')]))
"""
    paths = json.loads(docker("exec", backend, "python", "-c", script))
    destination = staging / "staticfiles"
    destination.mkdir()
    docker("cp", f"{backend}:/tmp/static-cache/.", str(destination))
    return paths


def check_static_cache(url, context, hashed_paths):
    for path in [*hashed_paths, "/static/website/css/site.css", "/static/website/js/site.js"]:
        request = Request(url + path, headers={"Host": "example.test"})
        with urlopen(request, context=context, timeout=5) as response:
            check_security_headers(response.headers)
            expected = "public, max-age=2592000, immutable" if path in hashed_paths else "no-cache"
            assert response.headers.get_all("Cache-Control") == [expected], response.headers
            assert response.headers.get("Expires") is None, response.headers
            assert response.read(), path
    for path in ("/static/missing.css", "/static/missing.0123456789ab.css"):
        request = Request(url + path, headers={"Host": "example.test"})
        try:
            with urlopen(request, context=context, timeout=5) as response:
                raise AssertionError(f"Expected 404 for {path}, got {response.status}")
        except HTTPError as error:
            with error:
                assert error.code == 404, error.code
                check_security_headers(error.headers)
                assert error.headers.get("Cache-Control") is None, error.headers
    print("PASS: hashed assets have immutable cache; unversioned assets require revalidation.")
    print("PASS: security headers are present on proxy responses, static files and static 404s.")


def start_backend(name, marker, network, app_image, containers):
    docker(
        "create",
        "--name",
        name,
        "--network",
        network,
        "--network-alias",
        "django-web",
        "--entrypoint",
        "python",
        app_image,
        "-u",
        "-c",
        BACKEND,
        marker,
    )
    containers.append(name)
    docker("start", name)
    return json.loads(docker("inspect", name))[0]["NetworkSettings"]["Networks"][network][
        "IPAddress"
    ]


def prepare_certificates(backend, staging):
    certificates = staging / "etc/letsencrypt/live/example.test"
    certificates.mkdir(parents=True)
    docker(
        "exec",
        backend,
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-days",
        "1",
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost",
        "-keyout",
        "/tmp/test-key.pem",
        "-out",
        "/tmp/test-cert.pem",
    )
    for source, destination in (
        ("test-key.pem", "privkey.pem"),
        ("test-cert.pem", "fullchain.pem"),
    ):
        docker("cp", f"{backend}:/tmp/{source}", str(certificates / destination))
    return certificates


def prepare_proxy_files(backend, staging):
    project = staging / "etc/nginx/project"
    project.mkdir(parents=True)
    (project / "nginx.conf").write_bytes((ROOT / "nginx.conf").read_bytes())
    (project / "security-headers.conf").write_bytes(
        (ROOT / "deploy/nginx-security-headers.conf").read_bytes()
    )
    hashed_paths = prepare_static_files(backend, staging)
    # Docker cp preserves source bytes; normalize shell scripts for Windows checkouts.
    for name in ("render-nginx.sh", "nginx-entrypoint.sh"):
        destination = (
            staging
            / "usr/local/bin"
            / ("render-nginx" if name == "render-nginx.sh" else "project-nginx-entrypoint")
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / "deploy" / name).read_bytes().replace(b"\r\n", b"\n"))
    return hashed_paths


def start_proxy(proxy, network, nginx_image, staging, containers):
    docker(
        "create",
        "--name",
        proxy,
        "--network",
        network,
        "-p",
        "127.0.0.1::443",
        "-e",
        "LETSENCRYPT_DOMAIN=example.test",
        "--entrypoint",
        "/bin/sh",
        nginx_image,
        "/usr/local/bin/project-nginx-entrypoint",
    )
    containers.append(proxy)
    docker("cp", str(staging) + "/.", proxy + ":/")
    docker("start", proxy)
    port = docker("port", proxy, "443/tcp").rsplit(":", 1)[1]
    return f"https://localhost:{port}"


def check_backend_switch(url, context, proxy, network, first, master_before):
    docker("network", "disconnect", network, first)
    wait_for_backend(url, context, "second")
    request = Request(
        url + "/contact/?source=dns-test",
        data=b"message=a%2Bb&name=Jan",
        headers={"Host": "example.test"},
    )
    with urlopen(request, context=context, timeout=5) as response:
        payload = json.load(response)
    assert payload == dict(
        backend="second",
        path="/contact/?source=dns-test",
        body="message=a%2Bb&name=Jan",
        method="POST",
        host="example.test",
        proto="https",
    ), payload
    assert docker("exec", proxy, "cat", "/var/run/nginx.pid") == master_before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-image", default="behawiorysta:test")
    args = parser.parse_args()
    # Read the image actually used by this project's Compose service.
    nginx_image = re.search(
        r"(?m)^    image: (nginx:\S+)\s*$", (ROOT / "docker-compose.yml").read_text()
    ).group(1)
    prefix = "nginx-integration-test-" + uuid.uuid4().hex[:12]
    network = prefix + "-network"
    first, second, proxy = (prefix + suffix for suffix in ("-first", "-second", "-proxy"))
    containers = []
    network_created = False
    try:
        docker("network", "create", network)
        network_created = True

        old_ip = start_backend(first, "first", network, args.app_image, containers)
        with tempfile.TemporaryDirectory(prefix=prefix) as directory:
            staging = Path(directory)
            certificates = prepare_certificates(first, staging)
            hashed_paths = prepare_proxy_files(first, staging)
            url = start_proxy(proxy, network, nginx_image, staging, containers)
            context = ssl.create_default_context(cafile=str(certificates / "fullchain.pem"))
            wait_for_backend(url, context, "first")
            docker("exec", proxy, "nginx", "-t")
            check_static_cache(url, context, hashed_paths)
            master_before = docker("exec", proxy, "cat", "/var/run/nginx.pid")
            new_ip = start_backend(second, "second", network, args.app_image, containers)
            assert new_ip != old_ip, (old_ip, new_ip)
            check_backend_switch(url, context, proxy, network, first, master_before)
            print(
                f"PASS: proxy recovered after backend IP changed {old_ip} -> {new_ip}; GET/POST preserved."
            )
    except Exception:
        for name in containers:
            try:
                logs = subprocess.run(
                    ["docker", "logs", "--tail", "30", name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                print(f"{name}:\n{logs.stdout}\n{logs.stderr}")
            except (OSError, subprocess.SubprocessError) as error:
                print(f"Could not collect logs for {name}: {error}")
        raise
    finally:
        cleanup_commands = [("rm", "--force", name) for name in reversed(containers)]
        if network_created:
            cleanup_commands.append(("network", "rm", network))
        cleanup_errors = []
        for command in cleanup_commands:
            try:
                docker(*command)
            except (OSError, subprocess.SubprocessError) as error:
                cleanup_errors.append(str(error))
        if cleanup_errors:
            message = "Docker cleanup failed: " + "; ".join(cleanup_errors)
            print(message)
            if sys.exception() is None:
                raise RuntimeError(message)


if __name__ == "__main__":
    main()
