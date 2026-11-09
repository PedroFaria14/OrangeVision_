import { Box, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

export function Brand({
  light = false,
  large = false,
}: {
  light?: boolean;
  large?: boolean;
}) {
  return (
    <Box
      component={Link}
      to="/"
      aria-label="OrangeVision — início do site"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1.2,
        textDecoration: 'none',
        color: light ? '#FFFFFF' : '#111827',
        width: 'fit-content',
        minHeight: 44,
      }}
    >
      <Box
        component="svg"
        viewBox="0 0 44 48"
        aria-hidden="true"
        sx={{ width: large ? 42 : 34, height: large ? 46 : 38, flexShrink: 0 }}
      >
        <path d="M23 10C24 3 30 1 34 2c-1 6-5 10-11 8Z" fill="#15803D" />
        <path
          d="M21 11c-3-3-6-3-9-2"
          fill="none"
          stroke="#15803D"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          d="M22 13C2 10 0 38 16 44c4 2 8 2 12 0 17-6 14-34-6-31Z"
          fill="#F97316"
        />
        <path
          d="M13 22c-3 3-4 7-3 10"
          fill="none"
          stroke="#FFE0BD"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </Box>
      <Typography
        component="span"
        sx={{
          fontFamily: 'Montserrat, sans-serif',
          fontSize: large ? 23 : 18,
          letterSpacing: '-.8px',
          fontWeight: 750,
        }}
      >
        OrangeVision
      </Typography>
    </Box>
  );
}
