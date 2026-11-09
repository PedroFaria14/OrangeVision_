import { Box, Stack, Typography } from '@mui/material';
import { useId, useState } from 'react';
import { Brand } from '@/shared/ui/Brand';

export function AuthVisual() {
  const id = useId().replace(/:/g, '');
  const configuredImage = String(import.meta.env.VITE_AUTH_IMAGE_URL || '');
  const image = /^\/(?!\/)[\w/.-]+$/.test(configuredImage)
    ? configuredImage
    : '';
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <Box
      component="aside"
      aria-label="Sobre o OrangeVision"
      sx={{
        position: 'relative',
        overflow: 'hidden',
        bgcolor: '#152820',
        color: 'white',
        minHeight: 640,
        p: { md: 5, lg: 7 },
        display: { xs: 'none', md: 'flex' },
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderRadius: '20px 0 0 20px',
      }}
    >
      {image && !imageFailed ? (
        <Box
          component="img"
          src={image}
          alt=""
          onError={() => setImageFailed(true)}
          sx={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: 0.48,
          }}
        />
      ) : (
        <Box
          component="svg"
          viewBox="0 0 600 740"
          aria-hidden="true"
          sx={{
            position: 'absolute',
            width: '125%',
            height: '100%',
            inset: '0 auto 0 -12%',
            opacity: 0.95,
          }}
        >
          <defs>
            <radialGradient id={`${id}-orange`} cx=".35" cy=".28" r=".8">
              <stop stopColor="#FFC665" />
              <stop offset=".55" stopColor="#F88A23" />
              <stop offset="1" stopColor="#D14F0B" />
            </radialGradient>
            <linearGradient id={`${id}-leaf`} x2="1" y2="1">
              <stop stopColor="#7B9B55" />
              <stop offset="1" stopColor="#244A31" />
            </linearGradient>
          </defs>
          <circle
            cx="305"
            cy="310"
            r="240"
            fill="none"
            stroke="#ffffff"
            strokeOpacity=".08"
          />
          <circle
            cx="305"
            cy="310"
            r="193"
            fill="none"
            stroke="#ffffff"
            strokeOpacity=".08"
          />
          <path
            d="M294 139c-56-81-156-58-175-27 32 69 111 84 175 27Z"
            fill={`url(#${id}-leaf)`}
          />
          <path
            d="M309 137c27-101 118-103 167-78-5 71-87 109-167 78Z"
            fill={`url(#${id}-leaf)`}
          />
          <circle cx="307" cy="315" r="147" fill={`url(#${id}-orange)`} />
          <circle cx="116" cy="481" r="104" fill={`url(#${id}-orange)`} />
          <circle cx="512" cy="458" r="104" fill={`url(#${id}-orange)`} />
          <path
            d="M222 234c-28 20-47 56-49 85"
            fill="none"
            stroke="#FFDE9E"
            strokeWidth="9"
            strokeLinecap="round"
            opacity=".5"
          />
          <path
            d="M174 226v-27h30m209 27v-27h-30M174 407v27h30m209-27v27h-30"
            fill="none"
            stroke="#F9E7B9"
            strokeWidth="2"
            strokeOpacity=".7"
          />
          <path d="M193 360h202" stroke="#FFF7DE" strokeOpacity=".45" />
        </Box>
      )}
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg,rgba(10,28,20,.12) 40%,rgba(10,28,20,.96) 95%)',
        }}
      />
      <Box sx={{ position: 'relative' }}>
        <Brand light />
        <Typography
          sx={{ mt: 1.5, fontSize: 12, letterSpacing: 2, color: '#D1E3D4' }}
        >
          TECNOLOGIA QUE OBSERVA.
        </Typography>
      </Box>
      <Stack spacing={2} sx={{ position: 'relative', maxWidth: 360 }}>
        <Typography
          sx={{
            color: '#FFC28F',
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: 1.4,
          }}
        >
          DO POMAR AOS DADOS
        </Typography>
        <Typography
          component="p"
          sx={{
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 650,
            fontSize: { md: 30, lg: 36 },
            lineHeight: 1.22,
            letterSpacing: '-1px',
          }}
        >
          Um novo olhar
          <br />
          para cada laranja.
        </Typography>
        <Typography sx={{ color: '#D8E3DB', fontSize: 14, lineHeight: 1.8 }}>
          Organize suas análises e acompanhe a triagem visual em um só lugar.
        </Typography>
        <Typography variant="caption" sx={{ color: '#ADBFB1', pt: 2 }}>
          Projeto acadêmico · Inspeção visual externa
          {(!image || imageFailed) && ' · Ilustração'}
        </Typography>
      </Stack>
    </Box>
  );
}
