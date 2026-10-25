import { useState, type FormEvent } from 'react';
import type { Filters } from '../api/analyses';
import { validateFilterForm } from '../model/filter_validation';

export function useFilterForm(apply: (filters: Filters) => void) {
  const [error, setError] = useState('');
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const filters = validateFilterForm(new FormData(event.currentTarget));
    if (!filters) {
      setError('Escolha um período válido de até 366 dias.');
      return;
    }
    setError('');
    apply(filters);
  }
  return { error, handleSubmit };
}
