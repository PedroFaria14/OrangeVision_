// Perfis e atuações fornecidos pela equipe para a página institucional.
export const teamIntroduction = {
  eyebrow: 'Nossa Equipe',
  title: 'Quem faz o OrangeVision acontecer',
  description:
    'Nossa equipe reúne estudantes de Engenharia da Computação com experiências profissionais em diferentes áreas da tecnologia e da indústria, combinando conhecimentos para desenvolver uma solução de visão computacional aplicada ao agronegócio.',
  course: 'Engenharia da Computação — USF',
} as const;

export type TeamMember = {
  id: string;
  name: string;
  initials: string;
  profession: string;
  biography: string;
  roles: readonly string[];
};

export const teamMembers = [
  {
    id: 'felipe-kenzo',
    name: 'Felipe Kenzo',
    initials: 'FK',
    profession: 'Estagiário em Projetos Automotivos na Flex',
    biography:
      'Participa do desenvolvimento de soluções relacionadas ao setor automotivo e aos processos de produção de componentes. Sua experiência no ambiente industrial, combinada à formação em Engenharia da Computação, contribui para o desenvolvimento de soluções tecnológicas e para a organização técnica do projeto.',
    roles: ['Software', 'Documentação'],
  },
  {
    id: 'kauan-fernandes',
    name: 'Kauan Fernandes',
    initials: 'KF',
    profession: 'Técnico de Redes na Global Hitss',
    biography:
      'Possui experiência na gestão de Backbone e CPEs, além da ativação, configuração e troubleshooting de roteadores e soluções SD-WAN. Trabalha com tecnologias como VMware VeloCloud, Huawei, Meraki, Fortinet, Cisco e HP, além de protocolos como BGP, OSPF e serviços MPLS, contribuindo para a disponibilidade e o desempenho de redes corporativas.',
    roles: ['Redes', 'Infraestrutura', 'Integração'],
  },
  {
    id: 'marcelo-capeletto',
    name: 'Marcelo Capeletto',
    initials: 'MC',
    profession: 'Estagiário em Garantia de Qualidade na EssilorLuxottica',
    biography:
      'Colabora com iniciativas voltadas a treinamento, comunicação e processos de melhoria contínua. Combinando formação acadêmica com experiência profissional, desenvolve competências em qualidade, gestão e excelência operacional em ambientes industriais.',
    roles: ['Qualidade', 'Testes', 'Documentação'],
  },
  {
    id: 'pedro-faria',
    name: 'Pedro Faria',
    initials: 'PF',
    profession: 'Estagiário em Desenvolvimento Blockchain no CPQD',
    biography:
      'Colabora no desenvolvimento de projetos envolvendo contratos inteligentes, criptografia e soluções descentralizadas. Combinando formação acadêmica com experiência em Web3, busca aplicar tecnologias emergentes no desenvolvimento de soluções digitais inovadoras.',
    roles: ['Software', 'Backend', 'Integração'],
  },
  {
    id: 'glauber-sandi-martins',
    name: 'Glauber Sandi Martins',
    initials: 'GS',
    profession: 'Product Development Specialist',
    biography:
      'Possui experiência em desenvolvimento e industrialização de produtos, NPI (New Product Introduction), gestão global de projetos, engenharia de manufatura e fabricação de produtos eletrônicos. Também atua no relacionamento e gerenciamento de clientes e fornecedores, integrando conhecimentos técnicos, industriais e de gestão de projetos.',
    roles: [
      'Desenvolvimento de Produto',
      'Industrialização',
      'Gestão de Projetos',
      'Integração',
    ],
  },
  {
    id: 'joao-assis',
    name: 'João Assis',
    initials: 'JA',
    profession: 'Técnico de Soluções Digitais Sr na Bosch',
    biography:
      'Possui formação como Técnico em Mecatrônica e experiência em IoT, conectividade e sistemas embarcados, combinando conhecimentos de hardware, software e comunicação para o desenvolvimento e integração de soluções digitais aplicadas a ambientes industriais.',
    roles: ['IoT', 'Sistemas Embarcados', 'Conectividade', 'Integração'],
  },
] as const satisfies readonly TeamMember[];

// Só inclui imagens realmente presentes: sem requisições a fotos inexistentes.
const photoModules = import.meta.glob<string>(
  '../../../assets/team/*.{webp,jpg,jpeg,png,avif}',
  { eager: true, query: '?url', import: 'default' },
);

export const teamPhotos: Partial<Record<string, string>> = Object.fromEntries(
  Object.entries(photoModules).map(([path, url]) => [
    path
      .split('/')
      .pop()!
      .replace(/\.[^.]+$/, ''),
    url,
  ]),
);
