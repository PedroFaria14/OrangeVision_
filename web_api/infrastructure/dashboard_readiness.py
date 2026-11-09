def inspect_dashboard(db, inspections_enabled):
    row = db.execute('''SELECT
        EXISTS(SELECT 1 FROM pg_attribute WHERE attrelid=to_regclass('orangevision_web.image_samples')
            AND attname='analysis_id' AND attnum>0 AND NOT attisdropped) AS column_exists,
        EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='orangevision_web'
            AND table_name='image_samples' AND column_name='analysis_id') AS column_visible,
        has_schema_privilege(current_user,'orangevision_web','USAGE') AS schema_usage,
        has_schema_privilege(current_user,'public','USAGE') AS public_schema_usage,
        has_table_privilege(current_user,to_regclass('public.analises'),'SELECT') AS analysis_read,
        has_table_privilege(current_user,to_regclass('public.analises'),'INSERT') AS analysis_write,
        has_table_privilege(current_user,to_regclass('orangevision_web.ingestion_receipts'),'INSERT') AS receipt_write,
        has_table_privilege(current_user,to_regclass('orangevision_web.inspection_sessions'),'SELECT') AS session_read,
        EXISTS(SELECT 1 FROM pg_constraint c JOIN pg_attribute a
            ON a.attrelid=c.conrelid AND a.attname='analysis_id' AND NOT a.attisdropped
            WHERE c.conrelid=to_regclass('orangevision_web.image_samples')
            AND c.confrelid=to_regclass('public.analises') AND c.contype='f'
            AND c.conkey=ARRAY[a.attnum]) AS link_fk,
        EXISTS(SELECT 1 FROM pg_index i JOIN pg_attribute a
            ON a.attrelid=i.indrelid AND a.attname='analysis_id' AND NOT a.attisdropped
            WHERE i.indrelid=to_regclass('orangevision_web.image_samples')
            AND i.indisunique AND i.indisvalid AND i.indnkeyatts=1
            AND i.indkey::smallint[] @> ARRAY[a.attnum]) AS link_unique,
        to_regclass('orangevision_web.effective_analyses') IS NOT NULL AS effective_view
    ''').fetchone()
    row['inspections_enabled'] = inspections_enabled
    row['link_access'] = False
    if row['column_exists']:
        row['link_access'] = db.execute('''SELECT
            has_column_privilege(current_user,'orangevision_web.image_samples','analysis_id','SELECT')
            AND has_column_privilege(current_user,'orangevision_web.image_samples','analysis_id','UPDATE') AS allowed''').fetchone()['allowed']
    row['view_access'] = not row['effective_view'] or db.execute(
        "SELECT has_table_privilege(current_user,'orangevision_web.effective_analyses','SELECT') AS allowed"
    ).fetchone()['allowed']
    status = 'enabled'
    if not inspections_enabled:
        status = 'inspections_disabled'
    elif not all(row[key] for key in ('column_exists', 'link_fk', 'link_unique')):
        status = 'schema_unavailable'
    elif not all(row[key] for key in ('column_visible', 'schema_usage', 'public_schema_usage', 'analysis_read', 'analysis_write', 'receipt_write', 'session_read', 'link_access', 'view_access')):
        status = 'permissions_missing'
    return {'status': status, 'checks': row}
