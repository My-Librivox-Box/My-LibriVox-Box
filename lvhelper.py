#!/usr/bin/env python3
"""
LibriVox Box download helper (for Termux).

The Internet Archive doesn't let web pages read its files directly, so the app can't
pull an MP3 itself to save into the folder you chose. This helper fetches the file on the
app's behalf and hands it straight back. It only fetches from archive.org and only listens
on this phone (127.0.0.1), so nothing else can use it.

Run:      python ~/lvhelper.py
Port:     8317 (change with LVHELPER_PORT)
"""
import os, sys, urllib.request, urllib.parse, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get('LVHELPER_PORT', '8317'))
VERSION = '1'
# hosts the helper will fetch from: the Internet Archive and its file servers (iaNNNNNN.us.archive.org)
ALLOWED = tuple(h.strip().lower() for h in os.environ.get('LVHELPER_HOSTS', 'archive.org').split(',') if h.strip())
CHUNK = 64 * 1024


def allowed(url):
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or '').lower()
    return u.scheme in ('http', 'https') and any(host == h or host.endswith('.' + h) for h in ALLOWED)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Expose-Headers', 'Content-Length, Content-Type')
        # lets a website reach this phone-local helper (Chrome asks for this on requests to 127.0.0.1)
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def plain(self, code, text):
        body = text.encode()
        self.send_response(code)
        self.cors()
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path)
        if path.path == '/ping':
            return self.plain(200, 'lvhelper ' + VERSION)
        if path.path != '/fetch':
            return self.plain(404, 'not found')
        url = urllib.parse.parse_qs(path.query).get('url', [''])[0]
        if not allowed(url):
            return self.plain(403, 'only archive.org files')
        try:
            # urllib follows the archive's redirects to the file server for us
            req = urllib.request.Request(url, headers={'User-Agent': 'LibriVoxBox-helper/' + VERSION})
            with urllib.request.urlopen(req, timeout=60) as up:
                if not allowed(up.geturl()):
                    return self.plain(403, 'redirected off archive.org')
                self.send_response(200)
                self.cors()
                self.send_header('Content-Type', up.headers.get('Content-Type', 'application/octet-stream'))
                length = up.headers.get('Content-Length')
                if length:
                    self.send_header('Content-Length', length)
                else:
                    self.send_header('Transfer-Encoding', 'chunked')
                self.end_headers()
                while True:
                    chunk = up.read(CHUNK)
                    if not chunk:
                        break
                    if length:
                        self.wfile.write(chunk)
                    else:
                        self.wfile.write(b'%x\r\n%s\r\n' % (len(chunk), chunk))
                if not length:
                    self.wfile.write(b'0\r\n\r\n')
        except urllib.error.HTTPError as e:
            self.plain(502, 'archive.org answered %d' % e.code)
        except (BrokenPipeError, ConnectionResetError):
            pass   # the app cancelled
        except Exception as e:
            try:
                self.plain(502, 'fetch failed: %s' % e)
            except Exception:
                pass

    def log_message(self, fmt, *args):
        sys.stderr.write('lvhelper: ' + (fmt % args) + '\n')


if __name__ == '__main__':
    print('LibriVox Box helper on http://127.0.0.1:%d  (Ctrl+C to stop)' % PORT, flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
