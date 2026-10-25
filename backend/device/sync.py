import json
import random
import time

from .api import ApiFailure, Offline


class Synchronizer:
    def __init__(self, store, api, clock=time.time):
        self.store, self.api, self.clock = store, api, clock

    def once(self):
        now = self.clock()
        rows = self.store.due(now)
        if not rows:
            return 0
        try:
            result = self.api.ingest(
                self.store.grant(rows[0]['session_id']),
                [json.loads(row['payload']) for row in rows],
            )
            acknowledgements = {str(item['id']): item['status'] for item in result['items']}
        except (Offline, ApiFailure, KeyError, TypeError, ValueError) as exc:
            for row in rows:
                permanent = isinstance(exc, ApiFailure) and exc.status in (
                    400,
                    403,
                    404,
                    409,
                    413,
                    422,
                )
                if permanent:
                    self.store.mark(row['id'], 'quarantined', type(exc).__name__)
                else:
                    delay = min(300, 2 ** min(row['attempts'] + 1, 8)) + random.uniform(0, 1)
                    self.store.retry(
                        row,
                        now,
                        max(delay, getattr(exc, 'retry_after', None) or 0),
                        type(exc).__name__,
                    )
            return 0
        confirmed = 0
        for row in rows:
            status = acknowledgements.get(row['id'])
            if status in ('accepted', 'duplicate'):
                self.store.mark(row['id'], 'synced')
                confirmed += 1
            elif status in ('conflict', 'rejected'):
                self.store.mark(row['id'], 'quarantined', status)
            else:
                self.store.retry(row, now, 5, 'MissingAcknowledgement')
        return confirmed
