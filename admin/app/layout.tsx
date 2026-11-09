import type { Metadata } from 'next';
import '@prisma/studio-core/ui/index.css';
import './style.css';

export const metadata: Metadata = {
  title: 'OrangeVision · Banco de dados',
  description: 'Painel administrativo privado do OrangeVision.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
