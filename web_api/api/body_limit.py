"""Limite real de bytes antes do parse JSON dos endpoints do dispositivo."""

from starlette.responses import JSONResponse


class DeviceBodyLimit:
    def __init__(self, app, maximum=262144):
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        sample_upload = path in (
            '/api/samples',
            '/api/device/samples/capture',
            '/api/device/samples/review-capture',
        )
        sample_device = path.startswith('/api/device/samples/')
        if (
            scope['type'] != 'http'
            or scope.get('method') != 'POST'
            or (
                path not in ('/api/ingest/analyses', '/api/device/inspections/pair')
                and not sample_upload
                and not sample_device
            )
        ):
            await self.app(scope, receive, send)
            return
        maximum = 5242880 if sample_upload else 2200000 if sample_device else self.maximum
        messages, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > maximum:
                await JSONResponse({'detail': 'Lote excede o limite de bytes.'}, status_code=413)(
                    scope, receive, send
                )
                return
            messages.append(message)
            if not message.get('more_body', False):
                break

        async def replay():
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, send)
