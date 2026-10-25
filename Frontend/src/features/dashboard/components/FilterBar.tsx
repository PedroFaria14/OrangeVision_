import type { Filters } from '../api/analyses';
import { useFilterForm } from '../hooks/useFilterForm';
import { previousCalendarDay, recentPeriod } from '../model/period';
import styles from '@/shared/ui/dashboard.module.css';

export function FilterBar({
  filters,
  apply,
}: {
  filters: Filters;
  apply: (value: Filters) => void;
}) {
  const { error, handleSubmit } = useFilterForm(apply);
  return (
    <form className={styles.filters} onSubmit={handleSubmit}>
      <fieldset>
        <legend>Filtros · horário de Brasília</legend>
        <p className={styles.shortcuts}>
          {(
            [
              [1, 'Hoje'],
              [7, '7 dias'],
              [30, '30 dias'],
            ] as const
          ).map(([days, label]) => (
            <button
              type="button"
              key={days}
              onClick={() => apply({ ...filters, ...recentPeriod(days) })}
            >
              {label}
            </button>
          ))}{' '}
          <button
            type="button"
            onClick={() => apply({ ...recentPeriod(30), classification: '' })}
          >
            Limpar filtros
          </button>
        </p>
        <div className={styles.filterFields}>
          <p>
            <label htmlFor="filter-start">Data inicial</label>{' '}
            <input
              id="filter-start"
              name="start"
              type="date"
              defaultValue={filters.start.slice(0, 10)}
              required
            />
          </p>
          <p>
            <label htmlFor="filter-end">Data final (inclusive)</label>{' '}
            <input
              id="filter-end"
              name="end"
              type="date"
              defaultValue={previousCalendarDay(filters.end)}
              required
            />
          </p>
          <p>
            <label htmlFor="filter-class">Classificação</label>{' '}
            <select
              id="filter-class"
              name="classification"
              defaultValue={filters.classification}
            >
              <option value="">Todas</option>
              <option value="APROVADA">Aprovada</option>
              <option value="ATENCAO">Atenção</option>
              <option value="REVISAR">Revisar</option>
            </select>
          </p>
          <button type="submit">Aplicar filtros</button>
        </div>
        {error && <p role="alert">{error}</p>}
      </fieldset>
    </form>
  );
}
