import type { IconName } from '@/shared/ui/Icon';

export const classifications = {
  APROVADA: {
    label: 'Aprovada',
    plural: 'Aprovadas',
    color: '#176B42',
    background: '#EFFAF3',
    border: '#D8EFE1',
    icon: 'check',
  },
  ATENCAO: {
    label: 'Atenção',
    plural: 'Atenção',
    color: '#8E570D',
    background: '#FFFBEF',
    border: '#F5EAC9',
    icon: 'warning',
  },
  REVISAR: {
    label: 'Revisar',
    plural: 'Revisar',
    color: '#AF3235',
    background: '#FEF2F2',
    border: '#F5DCDC',
    icon: 'close',
  },
} satisfies Record<
  string,
  {
    label: string;
    plural: string;
    color: string;
    background: string;
    border: string;
    icon: IconName;
  }
>;
