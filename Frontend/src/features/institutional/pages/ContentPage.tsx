import { Alert, Box, Chip, Paper, Stack, Typography } from '@mui/material';
import { Page } from '@/shared/ui/Page';
import { DevelopmentOverview } from '../components/DevelopmentOverview';
import { ProjectOverview } from '../components/ProjectOverview';
import { PlanningOverview } from '../components/PlanningOverview';
import { TeamOverview } from '../components/TeamOverview';
import { ReferencesOverview } from '../components/ReferencesOverview';
import { institutionalContent, type ContentSlug } from '../model/content';
export default function ContentPage({ slug }: { slug: ContentSlug }) {
  if (slug === 'referencias') {
    const content = institutionalContent.referencias;
    return (
      <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
        <Page
          title={content.title}
          description={content.description}
          eyebrow="Fundamentação"
          centered
        >
          <ReferencesOverview />
        </Page>
      </Box>
    );
  }
  if (slug === 'equipe') {
    return (
      <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
        <Page title={institutionalContent.equipe.title}>
          <TeamOverview />
        </Page>
      </Box>
    );
  }
  if (slug === 'planejamento') {
    const content = institutionalContent.planejamento;
    return (
      <Box sx={{ maxWidth: 1050, mx: 'auto', minWidth: 0 }}>
        <Page
          title={content.title}
          description={content.description}
          eyebrow="OrangeVision"
        >
          <PlanningOverview />
        </Page>
      </Box>
    );
  }
  if (slug === 'desenvolvimento') {
    const content = institutionalContent.desenvolvimento;
    return (
      <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
        <Page
          title={content.title}
          description={content.description}
          eyebrow="OrangeVision"
          centered
        >
          <DevelopmentOverview />
        </Page>
      </Box>
    );
  }
  if (slug === 'projeto') {
    const content = institutionalContent.projeto;
    return (
      <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
        <Page
          title={content.title}
          description={content.description}
          eyebrow="OrangeVision"
          centered
        >
          <ProjectOverview />
          <Alert severity="info">{content.pending}</Alert>
        </Page>
      </Box>
    );
  }
  const content = institutionalContent[slug];
  return (
    <Page title={content.title} description={content.description}>
      {slug === 'resultados' && (
        <Chip
          label="Validação experimental pendente"
          variant="outlined"
          sx={{ alignSelf: 'flex-start' }}
        />
      )}
      <Stack
        sx={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr)',
          gap: 2,
          maxWidth: 860,
        }}
      >
        {content.sections.map(([title, text]) => (
          <Paper
            component="section"
            variant="outlined"
            key={title}
            sx={{ p: { xs: 2, sm: 3 }, height: '100%' }}
          >
            <Typography component="h2" variant="h6" gutterBottom>
              {title}
            </Typography>
            <Typography sx={{ lineHeight: 1.8, maxWidth: '75ch' }}>
              {text}
            </Typography>
          </Paper>
        ))}
      </Stack>
      <Alert severity="info">{content.pending}</Alert>
    </Page>
  );
}
