import { createTheme } from '@mui/material/styles';
import { tokens } from './tokens';
export const theme = createTheme({
  palette: {
    primary: {
      main: tokens.colors.orange,
      dark: '#B7470B',
      contrastText: tokens.colors.graphite,
    },
    secondary: { main: tokens.colors.green },
    success: { main: tokens.colors.green },
    warning: { main: '#9A3412' },
    error: { main: '#B91C1C' },
    text: {
      primary: tokens.colors.graphite,
      secondary: tokens.colors.mutedText,
    },
    divider: tokens.colors.border,
    background: { default: tokens.colors.surface, paper: tokens.colors.white },
  },
  spacing: tokens.spacing,
  shape: { borderRadius: tokens.radius },
  typography: {
    fontFamily: tokens.fonts.body,
    h1: {
      fontFamily: tokens.fonts.heading,
      fontWeight: 700,
      fontSize: 'clamp(2rem, 5vw, 3.5rem)',
    },
    h2: {
      fontFamily: tokens.fonts.heading,
      fontSize: '1.75rem',
      fontWeight: 700,
    },
    h3: {
      fontFamily: tokens.fonts.heading,
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: { fontSize: 16, fontWeight: 650, letterSpacing: '-.2px' },
    button: { textTransform: 'none', fontWeight: 700 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: ({ ownerState, theme }) => ({
          minHeight: 44,
          borderRadius: 8,
          fontSize: 13,
          transition: 'background-color 150ms ease, border-color 150ms ease',
          ...(ownerState.color === 'primary' &&
          ownerState.variant !== 'contained'
            ? {
                color:
                  ownerState.variant === 'outlined'
                    ? theme.palette.text.primary
                    : theme.palette.primary.dark,
                ...(ownerState.variant === 'outlined'
                  ? { borderColor: '#D6DEE6', backgroundColor: '#FFFFFF' }
                  : {}),
              }
            : {}),
        }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: tokens.colors.border, borderRadius: 12 },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          fontSize: 14,
          borderRadius: 8,
          backgroundColor: '#FCFDFE',
          '& .MuiOutlinedInput-notchedOutline': { borderColor: '#DCE3E9' },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#AAB8C5',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#B7470B',
          },
        },
        input: { paddingTop: 14, paddingBottom: 14 },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { fontSize: 14, '&.Mui-focused': { color: '#B7470B' } },
      },
    },
    MuiFormHelperText: {
      styleOverrides: {
        root: { marginLeft: 0, fontSize: 12, lineHeight: 1.6 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: '#F7F9FB',
          color: tokens.colors.mutedText,
          fontSize: 12,
          fontWeight: 600,
          borderBottom: '1px solid #E6EBF0',
          whiteSpace: 'nowrap',
        },
        body: { fontSize: 13, borderBottom: '1px solid #EDF0F4' },
      },
    },
    MuiAlert: { styleOverrides: { root: { borderRadius: 8, fontSize: 13 } } },
    MuiIconButton: {
      styleOverrides: { root: { minWidth: 44, minHeight: 44 } },
    },
    MuiLink: { styleOverrides: { root: { color: tokens.colors.green } } },
    MuiCssBaseline: {
      styleOverrides: {
        html: { scrollbarGutter: 'stable' },
        body: { margin: 0 },
        '*': { boxSizing: 'border-box' },
        img: { maxWidth: '100%', height: 'auto' },
        ':focus-visible': {
          outline: `3px solid ${tokens.colors.green}`,
          outlineOffset: 3,
        },
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': {
            animation: 'none !important',
            transition: 'none !important',
            scrollBehavior: 'auto !important',
          },
        },
      },
    },
  },
});
