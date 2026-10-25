import json
from .db import local_db, remote_db

TABLES = ('dispositivos', 'analises', 'eventos_sistema')


def sync_pending():
    counts = {}
    with local_db() as local:
        with remote_db() as remote:
            for table in TABLES:
                rows = local.execute(f'SELECT * FROM {table} WHERE sincronizado = 0 ORDER BY rowid LIMIT 500').fetchall()
                synced = 0
                for row in rows:
                    d = dict(row)
                    d.pop('sincronizado', None)
                    if table == 'eventos_sistema' and d.get('detalhes') is not None:
                        d['detalhes'] = json.loads(d['detalhes'])
                    cols = list(d)
                    values = [d[c] for c in cols]
                    placeholders = ', '.join(['%s'] * len(cols))
                    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
                    with remote.transaction():
                        with remote.cursor() as cur:
                            cur.execute(sql, values)
                    local.execute(f'UPDATE {table} SET sincronizado = 1 WHERE id = ?', (row['id'],))
                    local.commit()
                    synced += 1
                counts[table] = synced
    return counts
