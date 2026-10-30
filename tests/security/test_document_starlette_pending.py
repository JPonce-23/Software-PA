"""Native local FileResponse checks, skipped when Starlette is unavailable.

No DB/app imports or server/network. The second test documents the CURRENT
path-reopen race; passing it is evidence of risk, never acceptance of a fix.
"""

import asyncio
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('starlette') is not None, 'Native Starlette unavailable; download QA pending')
class FileResponsePendingTests(unittest.TestCase):
    def response(self, path):
        from starlette.responses import FileResponse
        return FileResponse(path, filename='synthetic.pdf', media_type='application/octet-stream',
            content_disposition_type='attachment', headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store'})

    def collect(self, response):
        messages = []
        async def send(message): messages.append(message)
        async def receive(): return {'type': 'http.disconnect'}
        scope = {'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.4'},
                 'method': 'GET', 'path': '/download', 'headers': [], 'query_string': b''}
        asyncio.run(response(scope, receive, send))
        return messages

    def test_actual_attachment_binary_nosniff_private_headers(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'synthetic.pdf'; path.write_bytes(b'SS12 synthetic bytes')
            messages = self.collect(self.response(path))
            headers = dict(messages[0]['headers'])
            self.assertEqual(headers[b'content-type'], b'application/octet-stream')
            self.assertTrue(headers[b'content-disposition'].startswith(b'attachment'))
            self.assertEqual(headers[b'x-content-type-options'], b'nosniff')
            self.assertEqual(headers[b'cache-control'], b'private, no-store')

    def test_current_path_based_download_can_observe_substituted_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'original.pdf'; path.write_bytes(b'original-synthetic')
            checked = path.resolve(); self.assertTrue(checked.is_file())
            response = self.response(checked)
            replacement = Path(root) / 'replacement'; replacement.write_bytes(b'replacement-synthetic')
            os.replace(replacement, path)  # Both files belong only to this fixture.
            messages = self.collect(response)
            body = b''.join(message.get('body', b'') for message in messages if message['type'] == 'http.response.body')
            self.assertEqual(body, b'replacement-synthetic')


if __name__ == '__main__': unittest.main()
