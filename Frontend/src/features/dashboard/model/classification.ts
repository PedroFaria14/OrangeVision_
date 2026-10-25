export const classifications = {
  APROVADA: {
    label: 'Aprovada',
    plural: 'Aprovadas',
  },
  ATENCAO: {
    label: 'Atenção',
    plural: 'Atenção',
  },
  REVISAR: {
    label: 'Revisar',
    plural: 'Revisar',
  },
} satisfies Record<
  string,
  {
    label: string;
    plural: string;
  }
>;
