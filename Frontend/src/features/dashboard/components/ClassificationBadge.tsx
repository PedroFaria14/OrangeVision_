import { Chip } from '@mui/material';
import { classifications } from '../model/classification';
export function ClassificationBadge({
  value,
}: {
  value: keyof typeof classifications;
}) {
  return (
    <Chip
      size="small"
      label={classifications[value].label}
      sx={{
        color: classifications[value].color,
        bgcolor: classifications[value].background,
        border: `1px solid ${classifications[value].border}`,
        borderRadius: '5px',
        fontSize: 12,
        fontWeight: 650,
        textTransform: 'uppercase',
        letterSpacing: 0.2,
        height: 26,
      }}
    />
  );
}
