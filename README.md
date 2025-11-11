🤖 Nix – Bot de Chat para Twitch (Feita em Python)
Este é um projeto pessoal: uma bot chamada Nix, desenvolvida em Python, que responde automaticamente ao chat da Twitch. Você pode alterar o nome da bot, sua personalidade e outros comportamentos conforme desejar.
⚙️ Como configurar
- Pré-requisitos:
- Python 3.13.5 instalado no seu PC
- API Key da Groq salva no Windows
- Conta da Twitch e token de autenticação
- Instalação:
- Após configurar o básico, execute o arquivo run.bat
- Ele instalará todas as dependências automaticamente
- A Nix possui suporte a voz via TTS offline (pode ser desativado alterando tts = true para false)
🧠 Como a Nix funciona
- A Nix responde quando é mencionada no chat com a palavra "nix" ou com o nickname da conta Twitch logada (ex: nix_bot)
- Na área chamada PERSONA, você pode definir a personalidade da Nix. Exemplo:
"você se chama nix tomori"
- Sempre use aspas ("") e não apague nada fora delas, pois isso pode causar erros.
- A função de pesquisa permite que a Nix busque informações quando mencionada com a palavra "pesquise", mas essa funcionalidade está com problemas e pode não funcionar corretamente.
🧠 Tipos de memória da Nix
- Memória de contexto:
Lembra das últimas 20 mensagens de cada usuário para manter o contexto da conversa.
- Memória por palavras-chave:
Quando alguém diz algo como "eu gosto", ela armazena o que vem depois como uma preferência.
- Memória com comandos:
Usa comandos como !lembrar e !esquecer para guardar ou apagar informações prioritárias.
Exemplo:
nix !lembrar meu jogo favorito é Red Dead
nix !esquecer meu jogo favorito
- Memória comum:
Aprende sobre usuários específicos, como piadas internas, comportamentos e até apelidos.

📌 Resumo
Bot chamada Nix, feita em Python, que responde ao chat da Twitch com memória contextual, comandos personalizados e personalidade configurável
