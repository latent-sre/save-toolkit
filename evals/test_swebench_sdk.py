"""Use the real pinned Docker SDK against a loopback daemon protocol fixture."""

import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import docker
import pytest
from swebench_adapter.limits import BoundedContainer, bounded_exec


@pytest.fixture
def sdk_daemon(monkeypatch):
    identity = 'c' * 64
    calls = []
    socket_ready = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def reply(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlsplit(self.path)
            calls.append(('GET', url.path, parse_qs(url.query)))
            if url.path.endswith('/containers/json'):
                self.reply(200, [{'Id': identity, 'SizeRw': 256}])
            elif url.path.endswith('/exec/fixture-exec/json'):
                self.reply(200, {'Running': False, 'ExitCode': 0})
            else:
                self.reply(404, {'message': 'unexpected SDK request'})

        def do_POST(self):
            path = urlsplit(self.path).path
            size = int(self.headers.get('Content-Length', '0'))
            payload = json.loads(self.rfile.read(size) or b'{}')
            calls.append(('POST', path, payload))
            if path.endswith(f'/containers/{identity}/exec'):
                self.reply(201, {'Id': 'fixture-exec'})
            elif path.endswith('/exec/fixture-exec/start'):
                data = b'actual SDK stream\n'
                framed = b'\x01\x00\x00\x00' + struct.pack('>I', len(data)) + data
                self.send_response(101, 'Switching Protocols')
                self.send_header('Connection', 'Upgrade')
                self.send_header('Upgrade', 'tcp')
                self.send_header('Content-Type', 'application/vnd.docker.raw-stream')
                self.end_headers()
                self.wfile.flush()
                # Synchronize the simulated daemon with the SDK's HTTP-to-raw
                # transition; immediate fixture bytes can enter the HTTP header buffer.
                if not socket_ready.wait(2):
                    return
                self.wfile.write(framed)
                self.wfile.flush()
                self.close_connection = True
            elif path.endswith('/kill'):
                self.reply(204, {})
            else:
                self.reply(404, {'message': 'unexpected SDK request'})

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Explicit version prevents any discovery request outside this local protocol fixture.
    api = docker.APIClient(base_url=f'http://127.0.0.1:{server.server_port}', version='1.45', timeout=2)
    original_socket = api._get_raw_response_socket
    def raw_socket(response):
        result = original_socket(response)
        socket_ready.set()
        return result
    monkeypatch.setattr(api, '_get_raw_response_socket', raw_socket)
    raw = SimpleNamespace(id=identity, client=SimpleNamespace(api=api), kill=lambda: api.kill(identity))
    try:
        yield raw, calls
    finally:
        api.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_storage_and_output_boundaries_use_real_sdk_protocol(sdk_daemon):
    raw, calls = sdk_daemon
    text, timed_out, elapsed = bounded_exec(raw, ['printf', 'actual SDK stream'], timeout=3)
    assert text == 'actual SDK stream\n'
    assert timed_out is False
    assert elapsed < 3
    size_requests = [query for method, path, query in calls if method == 'GET' and path.endswith('/containers/json')]
    assert len(size_requests) >= 2
    for query in size_requests:
        assert query['size'] == ['1']
        assert query['all'] == ['1']
        assert json.loads(query['filters'][0]) == {'id': [raw.id]}
    assert not any(path.endswith('/kill') for _, path, _ in calls)


def test_wrapper_preserves_sdk_exec_options_and_byte_result(sdk_daemon):
    raw, calls = sdk_daemon
    result = BoundedContainer(raw).exec_run(['git', 'status'], user='root', workdir='/testbed', environment={'LC_ALL': 'C'})
    assert result.exit_code == 0
    assert result.output == b'actual SDK stream\n'
    created = next(body for method, path, body in calls if method == 'POST' and path.endswith('/exec'))
    assert created['Cmd'] == ['git', 'status']
    assert created['User'] == 'root'
    assert created['WorkingDir'] == '/testbed'
    assert created['Env'] == ['LC_ALL=C']
