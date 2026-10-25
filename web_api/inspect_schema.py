"""Inventário somente leitura. Não imprime conexão, credenciais nem dados pessoais."""

from .config import Settings
from .database import connection


def main():
    try:
        settings = Settings.load()
        with connection(settings) as db:
            db.execute('SET TRANSACTION READ ONLY')
            rows = db.execute("""SELECT table_schema,table_name,column_name,data_type
                FROM information_schema.columns WHERE table_name IN
                ('analises','dispositivos','users','sessions','device_access')
                ORDER BY table_schema,table_name,ordinal_position""").fetchall()
        for row in rows:
            print(
                f'{row["table_schema"]}.{row["table_name"]}.{row["column_name"]}: {row["data_type"]}'
            )
        print(f'Schema consultado: {len(rows)} colunas. Nenhum dado de usuário foi consultado.')
    except Exception as exc:
        print(f'Inspeção não concluída ({type(exc).__name__}). Nenhuma alteração executada.')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
