import { Avatar, Box, Paper, Stack, Typography } from '@mui/material';
import {
  teamIntroduction,
  teamMembers,
  teamPhotos,
  type TeamMember,
} from '../model/team';

function TeamMemberCard({ member }: { member: TeamMember }) {
  const photo = teamPhotos[member.id];
  return (
    <Paper
      component="article"
      aria-labelledby={`team-${member.id}`}
      sx={{
        p: { xs: 2.5, sm: 3 },
        minWidth: 0,
        height: '100%',
        borderTop: '5px solid',
        borderTopColor: 'primary.main',
        borderRadius: 2,
        boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Stack direction="row" sx={{ gap: 2, alignItems: 'center', mb: 2.5 }}>
        <Box sx={{ flexShrink: 0, textAlign: 'center' }}>
          <Avatar
            src={photo}
            alt=""
            aria-hidden="true"
            variant="rounded"
            slotProps={{ img: { loading: 'lazy', decoding: 'async' } }}
            sx={{
              width: { xs: 64, sm: 88 },
              height: { xs: 64, sm: 88 },
              bgcolor: '#FFF7ED',
              color: 'primary.dark',
              fontSize: { xs: 22, sm: 28 },
              fontWeight: 700,
              border: '1px solid #FED7AA',
              '& img': { objectFit: 'cover' },
            }}
          >
            {member.initials}
          </Avatar>
          {!photo && (
            <Typography
              component="span"
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mt: 0.5, fontSize: 11 }}
            >
              Sem foto
            </Typography>
          )}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography
            component="h3"
            variant="h3"
            id={`team-${member.id}`}
            sx={{ fontSize: { xs: 20, sm: 24 }, overflowWrap: 'anywhere' }}
          >
            {member.name}
          </Typography>
          <Typography
            variant="body2"
            color="secondary.main"
            sx={{ mt: 1, fontWeight: 700, lineHeight: 1.7 }}
          >
            {teamIntroduction.course}
          </Typography>
        </Box>
      </Stack>
      <Typography color="text.secondary" sx={{ fontSize: 15, lineHeight: 1.8 }}>
        Cursando o{' '}
        <Box component="strong" sx={{ color: 'text.primary' }}>
          3º ano de Engenharia da Computação na USF
        </Box>{' '}
        e atuando como{' '}
        <Box component="strong" sx={{ color: 'text.primary' }}>
          {member.profession}
        </Box>
        . {member.biography}
      </Typography>
      <Box sx={{ mt: 'auto', pt: 3 }}>
        <Box sx={{ borderTop: '1px solid', borderTopColor: 'divider', pt: 2 }}>
          <Typography
            variant="body2"
            color="primary.dark"
            sx={{ fontWeight: 700, mb: 1 }}
          >
            Atuação no OrangeVision
          </Typography>
          <Typography sx={{ fontSize: 14, lineHeight: 1.8 }}>
            {member.roles.join(' • ')}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}

export function TeamOverview() {
  return (
    <Stack spacing={4}>
      <Box
        component="section"
        aria-labelledby="team-introduction"
        sx={{ textAlign: 'center', py: { xs: 1, sm: 2 } }}
      >
        <Typography
          variant="overline"
          color="primary.dark"
          sx={{ letterSpacing: 2, fontWeight: 700 }}
        >
          {teamIntroduction.eyebrow}
        </Typography>
        <Typography
          component="h2"
          variant="h2"
          id="team-introduction"
          sx={{ mt: 1, fontSize: { xs: 26, sm: 32 }, lineHeight: 1.3 }}
        >
          {teamIntroduction.title}
        </Typography>
        <Box
          aria-hidden="true"
          sx={{
            width: 55,
            height: 4,
            bgcolor: 'secondary.main',
            borderRadius: 2,
            mx: 'auto',
            my: 2.5,
          }}
        />
        <Typography
          color="text.secondary"
          sx={{ maxWidth: 760, mx: 'auto', lineHeight: 1.8 }}
        >
          {teamIntroduction.description}
        </Typography>
      </Box>
      <Box
        component="section"
        aria-label="Integrantes da equipe OrangeVision"
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'minmax(0, 1fr)',
            md: 'repeat(2, minmax(0, 1fr))',
          },
          gap: 3,
        }}
      >
        {teamMembers.map((member) => (
          <TeamMemberCard member={member} key={member.id} />
        ))}
      </Box>
    </Stack>
  );
}
