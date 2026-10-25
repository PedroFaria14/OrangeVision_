from ..database import connection
from .analysis_mapping import adapt


def scope(user_id, filters, *, include_period=True, inspection_owner_only=False):
    clauses = [
        (
            'EXISTS (SELECT 1 FROM orangevision_web.inspection_sessions owned WHERE owned.user_id=%s AND owned.id=a.inspection_session_id)'
            if inspection_owner_only
            else 'EXISTS (SELECT 1 FROM orangevision_web.device_access da WHERE da.user_id=%s AND da.device_id=a.dispositivo_id)'
        ),
        "a.classificacao IN ('APROVADA','ATENCAO','REVISAR')",
    ]
    if not inspection_owner_only:
        # Compatível antes de 002 e seguro após desligar o recurso: registros com
        # sessão nunca voltam a ser compartilhados pela regra legada do dispositivo.
        clauses.append("(to_jsonb(a)->>'inspection_session_id') IS NULL")
    params = [user_id]
    for value, clause in (
        (filters.start if include_period else None, 'a.data_hora >= %s'),
        (filters.end if include_period else None, 'a.data_hora < %s'),
        (filters.classification, 'a.classificacao=%s'),
        (filters.device_id, 'a.dispositivo_id=%s'),
    ):
        if value is not None:
            clauses.append(clause)
            params.append(value)
    return ' AND '.join(clauses), params


class AnalysisRepository:
    def __init__(self, settings):
        self.settings = settings

    def list_analyses(self, user_id, filters, limit, offset):
        where, params = scope(
            user_id, filters, inspection_owner_only=self.settings.inspections_enabled
        )
        with connection(self.settings) as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            total = db.execute(
                f'SELECT count(*) AS total FROM analises a WHERE {where}', params
            ).fetchone()['total']
            rows = db.execute(
                f'SELECT a.* FROM analises a WHERE {where} ORDER BY a.data_hora DESC,a.id DESC LIMIT %s OFFSET %s',
                [*params, limit, offset],
            ).fetchall()
        return [adapt(row) for row in rows], total

    def find_analysis(self, user_id, analysis_id):
        ownership = (
            'EXISTS (SELECT 1 FROM orangevision_web.inspection_sessions owned WHERE owned.user_id=%s AND owned.id=a.inspection_session_id)'
            if self.settings.inspections_enabled
            else "EXISTS (SELECT 1 FROM orangevision_web.device_access da WHERE da.user_id=%s AND da.device_id=a.dispositivo_id) AND (to_jsonb(a)->>'inspection_session_id') IS NULL"
        )
        with connection(self.settings) as db:
            row = db.execute(
                f'SELECT a.* FROM analises a WHERE a.id=%s AND {ownership}',
                (analysis_id, user_id),
            ).fetchone()
        return adapt(row) if row else None

    def summarize(self, user_id, filters):
        where, params = scope(
            user_id, filters, inspection_owner_only=self.settings.inspections_enabled
        )
        with connection(self.settings) as db:
            return db.execute(
                f"""SELECT count(*) AS total,
                count(*) FILTER (WHERE classificacao='APROVADA') AS approved,
                count(*) FILTER (WHERE classificacao='ATENCAO') AS attention,
                count(*) FILTER (WHERE classificacao='REVISAR') AS review,
                max(data_hora) AS latest_analysis_at FROM analises a WHERE {where}""",
                params,
            ).fetchone()

    def aggregate_daily(self, user_id, filters):
        where, params = scope(
            user_id, filters, inspection_owner_only=self.settings.inspections_enabled
        )
        with connection(self.settings) as db:
            return db.execute(
                f"""SELECT date_trunc('day',a.data_hora AT TIME ZONE 'America/Sao_Paulo')
                AT TIME ZONE 'America/Sao_Paulo' AS start,
                count(*) FILTER (WHERE classificacao='APROVADA') AS approved,
                count(*) FILTER (WHERE classificacao='ATENCAO') AS attention,
                count(*) FILTER (WHERE classificacao='REVISAR') AS review
                FROM analises a WHERE {where} GROUP BY 1 ORDER BY 1""",
                params,
            ).fetchall()

    def compare_periods(self, user_id, filters, current, previous):
        # Ambos os períodos usam o mesmo snapshot e as mesmas permissões/filtros.
        # Os limites do período atual NÃO podem eliminar os registros do anterior.
        where, params = scope(
            user_id,
            filters,
            include_period=False,
            inspection_owner_only=self.settings.inspections_enabled,
        )
        with connection(self.settings) as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            rows = db.execute(
                f"""WITH periods(period_key,start_at,end_at) AS (
                VALUES ('current',%s::timestamptz,%s::timestamptz),
                       ('previous',%s::timestamptz,%s::timestamptz)
            )
            SELECT p.period_key, count(a.id) AS total,
                count(a.id) FILTER (WHERE a.classificacao='APROVADA') AS approved,
                count(a.id) FILTER (WHERE a.classificacao='ATENCAO') AS attention,
                count(a.id) FILTER (WHERE a.classificacao='REVISAR') AS review,
                max(a.data_hora) AS latest_analysis_at
            FROM periods p LEFT JOIN analises a
                ON a.data_hora>=p.start_at AND a.data_hora<p.end_at AND {where}
            GROUP BY p.period_key""",
                [
                    current.start,
                    current.observed_end,
                    previous.start,
                    previous.observed_end,
                    *params,
                ],
            ).fetchall()
        return {
            row['period_key']: {key: value for key, value in row.items() if key != 'period_key'}
            for row in rows
        }
