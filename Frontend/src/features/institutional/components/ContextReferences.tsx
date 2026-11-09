import { Box, Link, Paper, Stack, Typography } from '@mui/material';
import { contextReferences } from '../model/project';

export function ContextReferences() {
  return (
    <Box component="section" aria-labelledby="context-references-title">
      <Typography
        id="context-references-title"
        component="h2"
        variant="h6"
        sx={{ mb: 2 }}
      >
        Referências de contexto
      </Typography>
      <Box
        component="ul"
        sx={{ m: 0, p: 0, listStyle: 'none', display: 'grid', gap: 2 }}
      >
        {contextReferences.map((reference) => (
          <Paper
            component="li"
            variant="outlined"
            key={reference.url}
            sx={{ p: { xs: 2, sm: 3 }, minWidth: 0 }}
          >
            <Stack spacing={1}>
              <Typography component="h3" variant="h6" color="secondary.main">
                {reference.name}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.8, maxWidth: '75ch' }}
              >
                {reference.description}
              </Typography>
              <Link
                href={reference.url}
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  minHeight: 44,
                  width: 'fit-content',
                  maxWidth: '100%',
                  overflowWrap: 'anywhere',
                  fontWeight: 700,
                }}
              >
                {reference.linkLabel}
              </Link>
              {reference.note && (
                <Typography variant="caption" color="text.secondary">
                  {reference.note}
                </Typography>
              )}
            </Stack>
          </Paper>
        ))}
      </Box>
    </Box>
  );
}
