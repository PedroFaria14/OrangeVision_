export function signedNumber(value: number, digits = 1) {
  return new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: digits,
    signDisplay: 'exceptZero',
  }).format(value);
}
