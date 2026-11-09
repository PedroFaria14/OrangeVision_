import type { ReactNode } from 'react';
import { Box, Chip, Link, Paper, Stack, Typography } from '@mui/material';
import type { Theme } from '@mui/material/styles';
import { OrangeVisionDivider } from '@/shared/ui/OrangeVisionDivider';
import {
  developmentSections,
  type CategoryKey,
  type DevelopmentBlock,
  type DevelopmentSection,
  type FlowStep,
  type InfoCard,
  type Tone,
} from '../model/development';

const DARK = 'grey.900';
const accent = (tone: Tone) =>
  tone === 'green' ? 'secondary.main' : 'primary.main';
const labelColor = (tone: Tone) =>
  tone === 'green' ? 'secondary.main' : 'primary.dark';
const shadow = '0 4px 14px rgb(0 0 0 / 8%)';

const categoryStyle: Record<
  CategoryKey,
  { color: string; bg: string; icon: string }
> = {
  APROVADA: { color: '#166534', bg: '#F0FDF4', icon: '🟢' },
  ATENCAO: { color: '#92400E', bg: '#FFFBEB', icon: '🟡' },
  REVISAR: { color: '#991B1B', bg: '#FEF2F2', icon: '🔴' },
};
const tagStyle: Record<string, CategoryKey> = {
  Aprovada: 'APROVADA',
  Atenção: 'ATENCAO',
  Revisar: 'REVISAR',
};

function Emoji({ value, size = 30 }: { value: string; size?: number }) {
  return (
    <Box
      component="span"
      aria-hidden="true"
      sx={{ fontSize: size, lineHeight: 1.3 }}
    >
      {value}
    </Box>
  );
}

function Flow({ steps }: { steps: readonly FlowStep[] }) {
  return (
    <Box
      component="ol"
      sx={{
        m: 0,
        p: 0,
        listStyle: 'none',
        display: 'grid',
        gap: 1.25,
        maxWidth: { xs: 520, lg: 'none' },
        mx: 'auto',
        width: '100%',
        // Só em telas bem largas vira uma linha com setas; antes disso, uma coluna.
        gridTemplateColumns: {
          xs: 'minmax(0, 1fr)',
          lg: `repeat(${steps.length}, minmax(0, 1fr))`,
        },
      }}
    >
      {steps.map((step, index) => {
        const dark = step.tone === 'dark';
        return (
          <Box
            component="li"
            key={step.title}
            sx={{
              position: 'relative',
              p: 2,
              textAlign: 'center',
              borderRadius: 2,
              border: 1,
              borderColor: dark ? DARK : 'divider',
              borderTop: 5,
              borderTopColor: dark ? 'primary.main' : accent(step.tone),
              bgcolor: dark ? DARK : 'background.paper',
              boxShadow: shadow,
              minWidth: 0,
              '&:not(:last-of-type)::after': {
                content: '"→"',
                position: 'absolute',
                color: 'primary.main',
                fontWeight: 700,
                fontSize: 20,
                right: { xs: '50%', lg: -14 },
                top: { xs: 'auto', lg: '50%' },
                bottom: { xs: -22, lg: 'auto' },
                transform: {
                  xs: 'translateX(50%) rotate(90deg)',
                  lg: 'translateY(-50%)',
                },
                zIndex: 1,
              },
              mb: { xs: index < steps.length - 1 ? 1.5 : 0, lg: 0 },
            }}
          >
            <Emoji value={step.icon} />
            <Typography
              component="span"
              sx={{
                display: 'block',
                fontWeight: 700,
                mt: 1,
                color: dark ? 'common.white' : 'text.primary',
                overflowWrap: 'anywhere',
              }}
            >
              {step.title}
            </Typography>
            <Typography
              variant="body2"
              sx={{ mt: 0.75, color: dark ? 'grey.300' : 'text.secondary' }}
            >
              {step.text}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

function BlockTitle({
  children,
  light = false,
}: {
  children: string;
  light?: boolean;
}) {
  return (
    <Typography
      component="h3"
      variant="overline"
      sx={{
        display: 'block',
        letterSpacing: 2,
        fontWeight: 700,
        color: light ? 'primary.light' : 'text.primary',
        mb: 1.5,
        textAlign: 'center',
      }}
    >
      {children}
    </Typography>
  );
}

function Card({
  item,
  side,
  heading,
}: {
  item: InfoCard;
  side: 'top' | 'left';
  heading: 'h3' | 'h4';
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: { xs: 2, sm: 2.5 },
        height: '100%',
        minWidth: 0,
        boxShadow: shadow,
        ...(side === 'top'
          ? { borderTop: 5, borderTopColor: accent(item.tone) }
          : { borderLeft: 5, borderLeftColor: accent(item.tone) }),
      }}
    >
      {item.icon && <Emoji value={item.icon} size={32} />}
      {item.label && (
        <Typography
          variant="overline"
          sx={{
            display: 'block',
            color: labelColor(item.tone),
            letterSpacing: 1.5,
            fontWeight: 700,
          }}
        >
          {item.label}
        </Typography>
      )}
      <Typography
        component={heading}
        variant="h6"
        sx={{ mb: 1, overflowWrap: 'anywhere', fontSize: { xs: 17, sm: 19 } }}
      >
        {item.title}
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ lineHeight: 1.75 }}
      >
        {item.text}
      </Typography>
      {item.tags && (
        <Stack direction="row" sx={{ mt: 2, gap: 0.75, flexWrap: 'wrap' }}>
          {item.tags.map((tag) => {
            const category = tagStyle[tag];
            const style = category ? categoryStyle[category] : null;
            return (
              <Chip
                key={tag}
                label={tag}
                size="small"
                sx={{
                  fontWeight: 700,
                  height: 'auto',
                  '& .MuiChip-label': { whiteSpace: 'normal', py: 0.5 },
                  color: style
                    ? style.color
                    : item.tone === 'green'
                      ? '#166534'
                      : '#9A3412',
                  bgcolor: style
                    ? style.bg
                    : item.tone === 'green'
                      ? '#F0FDF4'
                      : '#FFF7ED',
                }}
              />
            );
          })}
        </Stack>
      )}
    </Paper>
  );
}

function DarkBox({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        bgcolor: DARK,
        color: 'common.white',
        borderRadius: 2,
        p: { xs: 2.5, sm: 3.5 },
        minWidth: 0,
      }}
    >
      {children}
    </Box>
  );
}

function Block({ block }: { block: DevelopmentBlock }) {
  switch (block.kind) {
    case 'cards':
      return (
        <Box>
          {block.title && <BlockTitle>{block.title}</BlockTitle>}
          <Box
            sx={{
              display: 'grid',
              gap: 2,
              gridTemplateColumns: {
                xs: 'minmax(0, 1fr)',
                sm:
                  block.columns && block.columns > 2
                    ? 'repeat(2, minmax(0, 1fr))'
                    : 'minmax(0, 1fr)',
                md: `repeat(${block.columns ?? 3}, minmax(0, 1fr))`,
              },
            }}
          >
            {block.items.map((item) => (
              <Card
                key={item.title}
                item={item}
                side={block.accent}
                heading={block.title ? 'h4' : 'h3'}
              />
            ))}
          </Box>
        </Box>
      );
    case 'code':
      return (
        <DarkBox>
          <BlockTitle light>{block.title}</BlockTitle>
          <Box
            component="pre"
            tabIndex={0}
            aria-label={block.title}
            sx={{
              m: 0,
              overflowX: 'auto',
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: { xs: 12, sm: 14 },
              lineHeight: 1.8,
              whiteSpace: 'pre',
            }}
          >
            {block.text}
          </Box>
        </DarkBox>
      );
    case 'table':
      return (
        <Box>
          <BlockTitle>{block.title}</BlockTitle>
          <Box
            tabIndex={0}
            role="region"
            aria-label={block.title}
            sx={{
              overflowX: 'auto',
              borderRadius: 2,
              boxShadow: shadow,
              border: 1,
              borderColor: 'divider',
            }}
          >
            <Box
              component="table"
              sx={{ width: '100%', minWidth: 640, borderCollapse: 'collapse' }}
            >
              <Box
                component="thead"
                sx={{ bgcolor: DARK, color: 'common.white' }}
              >
                <tr>
                  {block.columns.map((column) => (
                    <Box
                      component="th"
                      key={column}
                      scope="col"
                      sx={{ p: 1.75, textAlign: 'left' }}
                    >
                      {column}
                    </Box>
                  ))}
                </tr>
              </Box>
              <tbody>
                {block.rows.map(([field, type, text], index) => (
                  <Box
                    component="tr"
                    key={field}
                    sx={{ borderTop: 1, borderColor: 'divider' }}
                  >
                    <Box
                      component="th"
                      scope="row"
                      sx={{
                        p: 1.75,
                        textAlign: 'left',
                        fontFamily: 'Consolas, Monaco, monospace',
                        fontSize: 14,
                        color: index % 2 ? 'secondary.main' : 'primary.dark',
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {field}
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        p: 1.75,
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {type}
                    </Box>
                    <Box
                      component="td"
                      sx={{ p: 1.75, color: 'text.secondary' }}
                    >
                      {text}
                    </Box>
                  </Box>
                ))}
              </tbody>
            </Box>
          </Box>
        </Box>
      );
    case 'chain':
      return (
        <DarkBox>
          <BlockTitle light>{block.title}</BlockTitle>
          <Box
            component="ol"
            sx={{
              m: 0,
              p: 0,
              listStyle: 'none',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 1,
            }}
          >
            {block.steps.map((step, index) => (
              <Box
                component="li"
                key={`${index}-${step}`}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  maxWidth: '100%',
                }}
              >
                {index > 0 && (
                  <Box
                    component="span"
                    aria-hidden="true"
                    sx={{ color: 'primary.main', fontWeight: 700 }}
                  >
                    →
                  </Box>
                )}
                <Box
                  component="span"
                  sx={{
                    px: 1.75,
                    py: 1,
                    borderRadius: 1.5,
                    bgcolor: 'grey.800',
                    border: 1,
                    borderColor: 'grey.700',
                    fontWeight: 700,
                    fontSize: 14,
                    overflowWrap: 'anywhere',
                  }}
                >
                  {step}
                </Box>
              </Box>
            ))}
          </Box>
          {block.note && (
            <Typography
              variant="body2"
              sx={{
                color: 'grey.300',
                textAlign: 'center',
                mt: 2.5,
                maxWidth: 760,
                mx: 'auto',
              }}
            >
              {block.note}
            </Typography>
          )}
        </DarkBox>
      );
    case 'categories':
      return (
        <DarkBox>
          <BlockTitle light>{block.title}</BlockTitle>
          <Typography
            variant="body2"
            sx={{
              color: 'grey.300',
              textAlign: 'center',
              maxWidth: 740,
              mx: 'auto',
              mb: 2.5,
            }}
          >
            {block.intro}
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gap: 1.75,
              gridTemplateColumns: {
                xs: 'minmax(0, 1fr)',
                sm: 'repeat(3, minmax(0, 1fr))',
              },
            }}
          >
            {block.items.map((item) => {
              const style = categoryStyle[item.key];
              return (
                <Box
                  key={item.key}
                  sx={{
                    bgcolor: style.bg,
                    borderRadius: 2,
                    p: 2.25,
                    textAlign: 'center',
                    minWidth: 0,
                  }}
                >
                  <Emoji value={style.icon} size={26} />
                  <Typography
                    component="h4"
                    variant="h6"
                    sx={{ color: style.color, mt: 0.5 }}
                  >
                    {item.title}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ color: 'grey.800', mt: 0.75 }}
                  >
                    {item.text}
                  </Typography>
                  {item.rule && (
                    <Typography
                      variant="body2"
                      sx={{ color: style.color, mt: 1.25, fontWeight: 700 }}
                    >
                      {item.rule}
                    </Typography>
                  )}
                </Box>
              );
            })}
          </Box>
          <Typography
            variant="body2"
            sx={{
              color: 'grey.300',
              mt: 2.5,
              p: 1.75,
              border: 1,
              borderColor: 'grey.700',
              borderRadius: 1.5,
              textAlign: 'center',
            }}
          >
            {block.note}
          </Typography>
        </DarkBox>
      );
    case 'callout':
      return (
        <Box
          sx={{
            p: { xs: 2.25, sm: 3 },
            bgcolor: '#FFF7ED',
            borderLeft: 6,
            borderLeftColor: 'primary.main',
            borderRadius: 2,
          }}
        >
          <Typography component="h3" variant="h6" sx={{ mb: 1 }}>
            {block.title}
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: 'grey.800', lineHeight: 1.8 }}
          >
            {block.text}
          </Typography>
        </Box>
      );
    case 'note':
      return (
        <Box
          sx={{
            p: { xs: 2.25, sm: 3 },
            bgcolor: 'secondary.main',
            borderRadius: 2,
            textAlign: 'center',
          }}
        >
          <Typography
            variant="body2"
            sx={{ color: 'common.white', lineHeight: 1.8 }}
          >
            <strong>{block.strong}</strong> {block.text}
          </Typography>
        </Box>
      );
    case 'sources':
      return (
        <Paper
          variant="outlined"
          sx={{ p: { xs: 2.25, sm: 3 }, bgcolor: 'grey.50' }}
        >
          <BlockTitle>{block.title}</BlockTitle>
          <Stack
            spacing={2.5}
            divider={<Box sx={{ borderTop: 1, borderColor: 'divider' }} />}
          >
            {block.items.map((source) => (
              <Box key={source.url}>
                <Typography
                  component="h4"
                  sx={{ fontWeight: 700, color: 'secondary.main', mb: 0.75 }}
                >
                  {source.name}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 1 }}
                >
                  {source.text}
                </Typography>
                <Link
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ fontWeight: 700 }}
                >
                  {source.label} ↗
                </Link>
              </Box>
            ))}
          </Stack>
        </Paper>
      );
  }
}

function Section({ section }: { section: DevelopmentSection }) {
  return (
    <Box
      component="section"
      id={section.id}
      aria-labelledby={`dev-${section.id}`}
      sx={{ scrollMarginTop: (theme: Theme) => theme.spacing(10), minWidth: 0 }}
    >
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography
          variant="overline"
          sx={{ color: 'primary.dark', letterSpacing: 2, fontWeight: 700 }}
        >
          {section.eyebrow}
        </Typography>
        <Typography
          id={`dev-${section.id}`}
          component="h2"
          variant="h3"
          sx={{ fontSize: { xs: 25, sm: 30 } }}
        >
          {section.title}
        </Typography>
        <Box
          sx={{
            width: 55,
            height: 4,
            bgcolor: 'secondary.main',
            borderRadius: 2,
            mx: 'auto',
            my: 2,
          }}
        />
        <Typography
          color="text.secondary"
          sx={{ maxWidth: 820, mx: 'auto', lineHeight: 1.75 }}
        >
          {section.intro}
        </Typography>
      </Box>
      <Stack spacing={3.5}>
        {section.flow && <Flow steps={section.flow} />}
        {section.blocks.map((block, index) => (
          <Block key={`${section.id}-${index}`} block={block} />
        ))}
      </Stack>
    </Box>
  );
}

export function DevelopmentOverview() {
  return (
    <Stack spacing={2}>
      <Box component="nav" aria-label="Seções do desenvolvimento">
        <Stack
          direction="row"
          sx={{ gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}
        >
          {developmentSections.map((section) => (
            <Chip
              key={section.id}
              component="a"
              href={`#${section.id}`}
              clickable
              label={section.nav}
              variant="outlined"
              sx={{
                color: 'primary.dark',
                borderColor: 'primary.main',
                fontWeight: 700,
              }}
            />
          ))}
        </Stack>
      </Box>
      <Stack spacing={0} divider={<OrangeVisionDivider />}>
        {developmentSections.map((section) => (
          <Section key={section.id} section={section} />
        ))}
      </Stack>
    </Stack>
  );
}
