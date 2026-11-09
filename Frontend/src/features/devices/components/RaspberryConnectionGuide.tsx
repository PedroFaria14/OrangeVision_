import { Box, Paper, Stack, Typography } from '@mui/material';

export function RaspberryConnectionGuide() {
  return (
    <Paper
      component="section"
      aria-labelledby="raspberry-connection-title"
      variant="outlined"
      sx={{ p: { xs: 2, sm: 3 } }}
    >
      <Stack spacing={2}>
        <Typography id="raspberry-connection-title" component="h2" variant="h6">
          Como conectar seu Raspberry
        </Typography>
        <Typography variant="body2" color="text.secondary">
          O cadastro é feito aqui no site. Depois, o programa no Raspberry usa
          os dados gerados para se identificar e se conectar à Web API pela
          internet.
        </Typography>
        <Box component="ol" sx={{ m: 0, pl: 3, '& > li + li': { mt: 2 } }}>
          <li>
            <Typography component="h3" variant="subtitle2">
              Cadastre o equipamento no site
            </Typography>
            <Typography variant="body2">
              Informe um nome no formulário. O site gera o ID do equipamento e
              uma credencial de conexão vinculados à sua conta.
            </Typography>
          </li>
          <li>
            <Typography component="h3" variant="subtitle2">
              Guarde os três dados de conexão
            </Typography>
            <Typography variant="body2">
              Copie o ID, a URL da Web API e a credencial mostrados após o
              cadastro. A credencial só é exibida nessa confirmação. O ID
              sozinho não autoriza a conexão.
            </Typography>
          </li>
          <li>
            <Typography component="h3" variant="subtitle2">
              Configure o programa no Raspberry
            </Typography>
            <Typography variant="body2">
              Abra o OrangeVision no Raspberry. Se a sua versão oferecer uma
              configuração inicial, informe esses três valores quando
              solicitado. Nas versões sem esse assistente, preencha o arquivo
              device/.env dentro da pasta backend com a configuração copiada e
              reinicie o programa.
            </Typography>
          </li>
          <li>
            <Typography component="h3" variant="subtitle2">
              Confira a comunicação e escolha o que executar
            </Typography>
            <Typography variant="body2">
              Verifique no programa local se a API aceitou a conexão. Para uma
              inspeção, inicie a sessão no site e informe o código temporário no
              Raspberry. Esse código é diferente da credencial de conexão.
              Cadastrar ou copiar os dados não abre a câmera nem inicia uma
              inspeção.
            </Typography>
          </li>
        </Box>
        <Box component="details">
          <Typography
            component="summary"
            variant="subtitle2"
            sx={{ cursor: 'pointer', py: 1.5 }}
          >
            Não conseguiu conectar ou perdeu a credencial?
          </Typography>
          <Stack spacing={1.5} sx={{ pt: 1 }}>
            <Typography variant="body2">
              <strong>Sem internet ou API indisponível:</strong> mantenha os
              dados salvos, confira a rede e tente novamente. Não é necessário
              cadastrar outro equipamento nem gerar outra credencial por uma
              falha de rede.
            </Typography>
            <Typography variant="body2">
              <strong>Credencial recusada ou perdida:</strong> no cartão do seu
              equipamento, use Gerar nova credencial. A anterior será revogada;
              atualize o programa no Raspberry com a nova e reinicie-o. O ID e o
              histórico serão preservados.
            </Typography>
            <Typography variant="body2">
              <strong>Equipamento compartilhado ou antigo:</strong> solicite a
              configuração ao responsável. Ter acesso no site não permite
              recuperar a credencial nem assumir a propriedade do equipamento.
            </Typography>
          </Stack>
        </Box>
      </Stack>
    </Paper>
  );
}
