# WhatsApp Pizza Mania - Sistema de Envio Automatizado

Sistema automatizado para envio de mensagens WhatsApp para clientes da Pizza Mania.

## Funcionalidades

- Geração automática de mensagens personalizadas usando IA (Gemini)
- Envio automatizado para múltiplos contatos via WhatsApp Web
- Interface gráfica intuitiva
- Suporte a múltiplos navegadores (Chrome, Firefox, Edge)
- Proteção por serial único por máquina
- Preview e edição de mensagens
- Status de envio em tempo real

## Requisitos

- Python 3.8 ou superior
- Navegador web (Chrome, Firefox ou Edge)
- Conta do WhatsApp
- Conexão com internet

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
cd webscraping-whatsapp
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Configuração Inicial

1. Clone o repositório
2. Copie o arquivo `config.template.json` para `config.json`
3. Na primeira execução, você será solicitado a fornecer:
   - Chave API do Gemini
   - Número do WhatsApp
   - Link do cardápio

### Dados Sensíveis

O arquivo `config.json` contém dados sensíveis e está incluído no `.gitignore`.
Nunca compartilhe ou commite este arquivo.

### Variáveis de Configuração

- `api_key`: Sua chave API do Gemini
- `whatsapp.number`: Número do WhatsApp para contato
- `whatsapp.menu_link`: Link do cardápio online

### Segurança

- O arquivo `config.json` é criado localmente
- Dados sensíveis nunca são commitados
- Sessões do WhatsApp são armazenadas localmente
- O serial é único por máquina

## Como Usar

1. Execute o programa:
```bash
python app.py
```

2. Na primeira execução:
   - O sistema solicitará validação do serial
   - O serial é gerado automaticamente baseado no hardware

3. Para enviar mensagens:
   - Selecione um arquivo CSV com os contatos
   - Clique em "Gerar Mensagem" para criar uma mensagem personalizada
   - Preview a mensagem e ajuste se necessário
   - Clique em "Iniciar Envio" para começar o processo

## Formato do CSV

O arquivo CSV deve conter as seguintes colunas:
```csv
name,phone
João,5567999999999
Maria,5567999999999
```

## Recursos de Segurança

- Validação de serial por hardware
- Sessão persistente do WhatsApp
- Limpeza automática de processos

## Observações

- Não feche o navegador durante o envio
- Aguarde o scan do QR Code do WhatsApp na primeira vez
- A sessão do WhatsApp é mantida entre execuções
- Mensagens são personalizadas com o nome do cliente

## Suporte

Em caso de problemas:
1. Verifique a conexão com internet
2. Garanta que o WhatsApp Web está funcionando
3. Verifique o formato do arquivo CSV
4. Certifique-se que o navegador não está bloqueado

## Licença

[Sua Licença]
