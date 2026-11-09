"""Diagnóstico da fila local de resultados do Raspberry (sem tokens nem imagens).

Uso, na pasta que contém device/ (feche antes a janela da câmera):

    app/.venv/bin/python3 -m device.pending              # lista o que está preso
    app/.venv/bin/python3 -m device.pending --testar     # tenta confirmar 1x e mostra o erro exato
    app/.venv/bin/python3 -m device.pending --marcar-confirmada <ID>

Enquanto houver um resultado local aguardando confirmação, o equipamento não reserva
amostras novas da fila. --marcar-confirmada só deve ser usado quando o site já mostra
o resultado daquela amostra (o servidor já o recebeu).
"""

import argparse
import sys
import traceback

from .config import DeviceSettings
from .locking import device_lock
from .storage import Store


def pending_rows(store):
    with store.db() as db:
        return [
            dict(row) for row in db.execute(
                "SELECT sample_id,confirmation,(payload IS NOT NULL) AS has_payload,"
                "analysis_id,updated_at FROM sample_status "
                "WHERE confirmation IN ('processing','pending') ORDER BY updated_at,rowid"
            )
        ]


def mark_confirmed(store, sample_id):
    with store.db() as db:
        changed = db.execute(
            "UPDATE sample_status SET confirmation='confirmed',payload=NULL,claim_id=NULL,"
            "lease_token=NULL WHERE (sample_id=? OR sample_id LIKE ?) "
            "AND confirmation IN ('processing','pending')",
            (sample_id, sample_id + '%'),
        ).rowcount
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description='Fila local de resultados do OrangeVision.')
    parser.add_argument('--testar', action='store_true', help='Tenta confirmar o item preso uma vez.')
    parser.add_argument('--marcar-confirmada', metavar='ID', help='Libera a fila marcando o item como confirmado.')
    args = parser.parse_args(argv)
    settings = DeviceSettings.load()
    store = Store(settings.database)
    store.initialize()
    rows = pending_rows(store)
    if not rows:
        print('Nenhum resultado local preso. O equipamento pode reservar amostras novas.')
    for row in rows:
        print(
            f'Preso: {row["sample_id"]} | estado local: {row["confirmation"]} | '
            f'resultado salvo: {"sim" if row["has_payload"] else "não"} | '
            f'analysis_id local: {row["analysis_id"] or "-"} | desde: {row["updated_at"]}'
        )
    if args.marcar_confirmada:
        with device_lock(store.path.with_suffix('.samples.lock')):
            changed = mark_confirmed(store, args.marcar_confirmada)
        print('Liberado.' if changed else 'Nada alterado: ID não encontrado entre os itens presos.')
        return 0 if changed else 1
    if args.testar and rows and not rows[0]['has_payload']:
        # Sem resultado salvo, testar reprocessaria a foto sem calibração/IA e enviaria isso.
        print('O primeiro item ainda não tem resultado salvo; abra a câmera para processá-lo.')
        return 1
    if args.testar and rows:
        from .api import DeviceApi
        from .samples import process_one

        api = DeviceApi(settings)
        try:
            result = process_one(api, None, validated=False, detector=None, store=store)
            print('Confirmação concluída:', result)
        except Exception as error:
            print(f'ERRO {type(error).__name__}: {error}')
            traceback.print_exc(limit=6, file=sys.stdout)
            return 1
        finally:
            api.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
