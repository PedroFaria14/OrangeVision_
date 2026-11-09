import { Typography } from '@mui/material';
import { formatNumber } from '@/shared/lib/format';
import type { CountChange } from '../api/comparison';
import { signedNumber } from '../model/comparison_format';

export function CountDelta({
  change,
  previous,
}: {
  change: CountChange;
  previous: number;
}) {
  if (previous === 0 && change.absolute === 0) return null;
  return (
    <Typography
      component="p"
      sx={{ fontSize: 12, mt: 1, color: 'text.secondary', lineHeight: 1.6 }}
    >
      Anterior: {formatNumber(previous, 0)}
      <br />
      <span>
        {signedNumber(change.absolute, 0)}{' '}
        {change.percent !== null
          ? `(${signedNumber(change.percent)}%)`
          : '· sem comparação percentual'}
      </span>
    </Typography>
  );
}
