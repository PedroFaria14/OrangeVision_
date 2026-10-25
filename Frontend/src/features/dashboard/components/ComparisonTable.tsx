import type { Comparison } from '../api/comparison';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { signedNumber } from '../model/comparison_format';
import { TableRegion } from '@/shared/ui/TableRegion';

export function ComparisonTable({ data }: { data: Comparison }) {
  const rows = [
    ['Total analisado', 'total'],
    ['Aprovadas', 'approved'],
    ['Atenção', 'attention'],
    ['Revisar', 'review'],
    ['Não aprovadas (Atenção + Revisar)', 'not_approved'],
  ] as const;
  return (
    <section>
      <h2>Período atual × anterior</h2>
      <p>
        Atual: {formatDate(data.current.start)} até{' '}
        {formatDate(data.current.end)} (fim exclusivo).
      </p>
      <p>
        Anterior: {formatDate(data.previous.start)} até{' '}
        {formatDate(data.previous.end)} (fim exclusivo).
      </p>
      {data.current.in_progress && (
        <p>
          Período atual em andamento: valores parciais até{' '}
          {formatDate(data.current.observed_end)}.
        </p>
      )}
      {data.current.total === 0 && data.previous.total === 0 ? (
        <p>Ainda não há dados para comparar nos dois períodos selecionados.</p>
      ) : (
        <TableRegion label="Rolagem da comparação entre períodos">
          <table>
            <caption>Comparação entre períodos</caption>
            <thead>
              <tr>
                <th scope="col">Indicador</th>
                <th scope="col">Atual</th>
                <th scope="col">Anterior</th>
                <th scope="col">Diferença absoluta</th>
                <th scope="col">Variação percentual</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, key]) => (
                <tr key={key}>
                  <th scope="row">{label}</th>
                  <td>{data.current[key]}</td>
                  <td>{data.previous[key]}</td>
                  <td>{signedNumber(data.changes[key].absolute)}</td>
                  <td>
                    {data.changes[key].percent === null
                      ? '—'
                      : `${signedNumber(data.changes[key].percent)}%`}
                  </td>
                </tr>
              ))}
              <tr>
                <th scope="row">Taxa de aprovação</th>
                <td>{formatRatio(data.current.approval_rate)}</td>
                <td>{formatRatio(data.previous.approval_rate)}</td>
                <td>
                  {data.changes.approval_rate_pp === null
                    ? '—'
                    : `${signedNumber(data.changes.approval_rate_pp)} p.p.`}
                </td>
                <td>Não se aplica</td>
              </tr>
            </tbody>
          </table>
        </TableRegion>
      )}
      <p>
        Base anterior zero: variação percentual indisponível. Taxa de aprovação
        não é acurácia.
      </p>
      <p>
        Consulta: {formatDate(data.as_of)}. Mesmos filtros e permissões nos dois
        períodos. Valores: {formatNumber(data.current.total, 0)} registros
        atuais.
      </p>
    </section>
  );
}
