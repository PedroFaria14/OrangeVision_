export const navigation = [
  ['/', 'Início'],
  ['/projeto', 'O Projeto'],
  ['/planejamento', 'Planejamento'],
  ['/desenvolvimento', 'Desenvolvimento'],
  ['/dashboard', 'Dashboard'],
  ['/resultados', 'Resultados'],
  ['/equipe', 'Equipe'],
  ['/referencias', 'Referências'],
] as const;
export function pageTitle(path: string) {
  if (path === '/login') return 'Entrar';
  if (path === '/registrar') return 'Criar conta';
  if (path === '/dashboard/perfil') return 'Meu perfil';
  if (path === '/dashboard/inspecoes') return 'Inspeções';
  if (path === '/dashboard/dispositivos') return 'Equipamentos';
  if (path === '/dashboard/amostras') return 'Amostras e imagens';
  if (path === '/dashboard/historico') return 'Histórico de análises';
  if (path.startsWith('/dashboard/analises/')) return 'Detalhe da análise';
  return (
    navigation.find(([url]) => url === path)?.[1] || 'Página não encontrada'
  );
}
