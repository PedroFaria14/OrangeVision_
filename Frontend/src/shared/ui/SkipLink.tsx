import { Link } from '@mui/material';
export function SkipLink() {
  return (
    <Link
      href="#conteudo"
      sx={{
        position: 'absolute',
        top: -100,
        left: 16,
        zIndex: 1600,
        bgcolor: 'background.paper',
        p: 2,
        '&:focus': { top: 8 },
      }}
    >
      Ir para o conteúdo
    </Link>
  );
}
