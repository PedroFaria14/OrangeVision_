import { Link } from 'react-router-dom';
import type { Analysis } from '../api/analyses';
import { classifications } from '../model/classification';
import { formatDate, formatNumber } from '@/shared/lib/format';
import { TableRegion } from '@/shared/ui/TableRegion';

export function AnalysesTable({
  items,
  total,
  offset,
  busy,
  changePage,
  compact = false,
}: {
  items: Analysis[];
  total: number;
  offset: number;
  busy: boolean;
  changePage: (value: number) => void;
  compact?: boolean;
}) {
  return (
    <section>
      <h2>{compact ? 'Últimas análises' : 'Histórico de análises'}</h2>
      <p>{total} registros no recorte.</p>
      {items.length === 0 ? (
        <p role="status">
          Nenhuma análise neste período ou página. Ajuste os filtros para
          consultar outro recorte.
        </p>
      ) : (
        <TableRegion label="Rolagem do histórico de análises">
          <table>
            <caption>Histórico de análises</caption>
            <thead>
              <tr>
                {[
                  'Data/hora',
                  'Classificação',
                  'Score experimental',
                  'Dispositivo',
                  'Consulta',
                ].map((label) => (
                  <th scope="col" key={label}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(compact ? items.slice(0, 5) : items).map((item) => (
                <tr key={item.id}>
                  <td>{formatDate(item.timestamp)}</td>
                  <td>{classifications[item.classification].label}</td>
                  <td>{formatNumber(item.metrics.visual_score)}</td>
                  <td>{item.device_id || 'Não informado'}</td>
                  <td>
                    <Link to={`/dashboard/analises/${item.id}`}>
                      Ver detalhes da análise {item.id.slice(0, 8)}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
      {!compact && total > 0 && (
        <nav aria-label="Paginação do histórico">
          <button
            disabled={!offset || busy}
            onClick={() => changePage(Math.max(0, offset - 20))}
          >
            Anterior
          </button>{' '}
          Página {Math.floor(offset / 20) + 1}{' '}
          <button
            disabled={offset + 20 >= total || busy}
            onClick={() => changePage(offset + 20)}
          >
            Próxima
          </button>
        </nav>
      )}
    </section>
  );
}
