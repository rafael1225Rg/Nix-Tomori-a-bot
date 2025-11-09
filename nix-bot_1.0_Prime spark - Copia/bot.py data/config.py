# ========== CONFIG BÁSICA DA NIX ==========

# Twitch
TWITCH_TOKEN = "TOKEN DA CONTA DA SUA NIX"   # ex: oauth:xxxxxxx
TWITCH_NICK  = "NOME DA CONTA DA SUA NIX"
TWITCH_CHAN  = "SEU CANAL DA TWITCH"

# Comportamento
CHAT_REPLY_ENABLED = True
TTS_ENABLED = True
MENTION_ONLY = True   # Nix só responde se citarem "nix"
MEMORY_ENABLED = True          # liga/desliga memória
MEMORY_DB_PATH = "memory.db"   # arquivo SQLite (pode levar no pendrive)

# Modelo IA (Groq)
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_KEY = None   # NÃO ALTERAR — ele lê do sistema

# Voz (Edge TTS)
VOICE_NAME = "pt-BR-ThalitaNeural"

# ===== Memória global (curto prazo do chat)
GLOBAL_CONTEXT_ENABLED = True       # liga/desliga contexto de sala
GLOBAL_CONTEXT_LIMIT   = 20        # quantas falas recentes entram no prompt
MAX_CONTEXT_CHARS      = 1200       # segurança pra não estourar o prompt

