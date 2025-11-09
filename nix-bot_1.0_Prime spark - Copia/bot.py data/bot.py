# Nix VTuber — IA + Voz + Twitch (Groq + Edge-TTS) — memória por usuário + global curto prazo

import os, re, time, asyncio, subprocess, pyttsx3, websockets, aiofiles
from groq import Groq
from config import *                 # TWITCH_*, flags, GROQ_MODEL etc.
from memory import Memory            # SQLite (facts/log + chatlog)
from websearch import web_search

# ===== defaults caso não existam no config.py =====
try:
    GLOBAL_CONTEXT_ENABLED
except NameError:
    GLOBAL_CONTEXT_ENABLED = True
try:
    GLOBAL_CONTEXT_LIMIT
except NameError:
    GLOBAL_CONTEXT_LIMIT = 20
try:
    MAX_CONTEXT_CHARS
except NameError:
    MAX_CONTEXT_CHARS = 1200

# ===== IA (Groq) =====
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def llm_reply(persona: str, context: str) -> str:
    # segurança extra: evita prompt gigante
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[-MAX_CONTEXT_CHARS:]
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": persona},
                {"role": "user",   "content": context},
            ],
            temperature=0.7,
            max_tokens=180,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("LLM error:", e)
        return "Dei uma bugada mental aqui, pera lá. "

# ===== MEMÓRIA (SQLite) =====
MEM = Memory(MEMORY_DB_PATH) if (MEMORY_ENABLED) else None

# ===== TTS (Edge + fallback local) =====
async def speak(text: str):
    if not TTS_ENABLED:
        return
    try:
        fname = "tts.mp3"
        from edge_tts import Communicate
        tts = Communicate(text, VOICE_NAME, rate="+10%")
        async with aiofiles.open(fname, "wb") as f:
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    await f.write(chunk["data"])
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", fname])
    except Exception:
        print("[TTS] Edge falhou — usando voz offline.")
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

# ===== Respostas prontas =====
CANNED = [
    (r"\b(oi|olá|ola)\b", [
        "Oi, oi, oi! ",
        "Cheguei brilhando ou é a luz do monitor? ",
    ]),
    (r"\b(!piada)\b", [
        "Eu tentei abrir o inventário da vida, mas só encontrei boleto. ",
    ])
]

def canned_reply(msg: str):
    import random
    for patt, answers in CANNED:
        if re.search(patt, msg, flags=re.I):
            return random.choice(answers)
    return None

# ===== Persona + Contexto (mem por usuário + global) =====
def craft_prompt(user: str, msg: str):
    persona = (
        "Você se chama nix tomori, não se sabe muito sobre você ainda"
    )

    mem_facts, mem_recent = [], ""
    global_block = ""
    if MEMORY_ENABLED and MEM:
        mem_facts  = MEM.list_facts(user, limit=15)
        mem_recent = MEM.recent_summary(user, limit=15)
        if GLOBAL_CONTEXT_ENABLED:
            recent_chat = MEM.recent_global(limit=GLOBAL_CONTEXT_LIMIT)
            if recent_chat:
                global_block = "Conversa recente no chat:\n" + recent_chat + "\n"

    mem_block = ""
    if mem_facts:
        mem_block += "Fatos lembrados sobre este viewer:\n- " + "\n- ".join(mem_facts) + "\n"
    if mem_recent:
        mem_block += "Conversas recentes com este viewer:\n" + mem_recent + "\n"

    # ordem: contexto global → mem por user → mensagem atual
    context = (
        f"{global_block}"
        f"{mem_block}"
        f"Viewer: {user}\n"
        f"Mensagem: {msg}\n"
        "Responda com humor leve e direto."
    )
    # corta se ficar grande
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[-MAX_CONTEXT_CHARS:]
    return persona, context

# ===== Twitch IRC =====
class TwitchChat:
    COOLDOWN = 2
    def __init__(self):
        self.ws = None
        self.cooldown = {}

    async def connect(self):
        self.ws = await websockets.connect("wss://irc-ws.chat.twitch.tv:443")
        await self.send(f"PASS {TWITCH_TOKEN}")
        await self.send(f"NICK {TWITCH_NICK}")
        await self.send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership")
        await self.send(f"JOIN #{TWITCH_CHAN}")
        print(f"[NIX] Conectada como {TWITCH_NICK} — ouvindo #{TWITCH_CHAN}")

    async def send(self, msg: str):
        await self.ws.send(msg + "\r\n")

    async def send_chat(self, msg: str):
        if CHAT_REPLY_ENABLED:
            await self.send(f"PRIVMSG #{TWITCH_CHAN} :{msg}")

    async def run(self):
        async for raw in self.ws:
            for line in raw.split("\r\n"):
                if not line:
                    continue
                if line.startswith("PING"):
                    await self.send("PONG :tmi.twitch.tv")
                    continue
                if "PRIVMSG" in line:
                    user, msg = self.parse_msg(line)
                    if user and msg:
                        await self.handle(user, msg)

    def parse_msg(self, line: str):
        m = re.search(r":([^!]+)!.* PRIVMSG #[^ ]+ :(.*)$", line)
        return (m.group(1), m.group(2)) if m else (None, None)

    async def handle(self, user: str, txt: str):
        # salva no log global ANTES de qualquer coisa
        if MEMORY_ENABLED and MEM and GLOBAL_CONTEXT_ENABLED:
            MEM.save_global(user, txt)

        # cooldown por usuário
        now = time.time()
        last = self.cooldown.get(user, 0)
        if now - last < self.COOLDOWN:
            return
        self.cooldown[user] = now

        low = txt.lower()

        # só responde se for mencionada
        if MENTION_ONLY and "nix" not in low and f"@{TWITCH_NICK}".lower() not in low:
            return

          # ======== Comando de pesquisa ========
        # aciona com "pesquise ..." ou "procure ..."
        low = txt.lower()
        if "pesquise" in low or "procure" in low:
            # pega o que vem após a palavra-chave
            if "pesquise" in low:
                termo = low.split("pesquise", 1)[-1].strip(" :–-–—")
            else:
                termo = low.split("procure", 1)[-1].strip(" :–-–—")

            if termo:
                resumo = web_search(termo)   # chamada síncrona (requests) -> OK
                reply  = f"Pesquisei e achei: {resumo}"
                await self.send_chat(reply)
                if TTS_ENABLED:
                    await speak(reply)
                return  # não cai no LLM



        # ===== Comandos de MEMÓRIA =====
        if low.startswith("!lembrar"):
            if not (MEMORY_ENABLED and MEM):
                await self.send_chat("Memória está desligada no config.")
                return
            fact = txt.split(" ", 1)[1] if " " in txt else ""
            if len(fact.strip()) < 3:
                await self.send_chat("Me diga *o que* lembrar: !lembrar gosto de Red Dead.")
                return
            MEM.remember_fact(user, fact.strip())
            await self.send_chat("Anotado na minha cabeça. ")
            return

        if low.startswith("!esquecer"):
            if not (MEMORY_ENABLED and MEM):
                await self.send_chat("Memória está desligada no config.")
                return
            text_like = txt.split(" ", 1)[1] if " " in txt else ""
            n = MEM.forget_fact(user, text_like.strip())
            await self.send_chat(f"Joguei {n} lembrança(s) no buraco negro. ️")
            return

        if low.startswith("!memoria"):
            if not (MEMORY_ENABLED and MEM):
                await self.send_chat("Memória está desligada no config.")
                return
            facts = MEM.list_facts(user, limit=10)
            if not facts:
                await self.send_chat("Ainda não lembro nada seu. Me conta algo com !lembrar ...")
            else:
                preview = " | ".join(facts[:5])
                await self.send_chat(f"Eu lembro: {preview}")
            return

        # respostas prontas
        canned = canned_reply(low)
        if canned:
            await self.send_chat(canned)
            await speak(canned)
            return

        # IA com contexto global + memória do usuário
        persona, ctx = craft_prompt(user, txt)
        reply = await llm_reply(persona, ctx)

        # salva histórico por usuário e extrai preferências
        if MEMORY_ENABLED and MEM:
            MEM.save_interaction(user, txt, reply)
            MEM.auto_extract_and_store(user, txt)

        print(f"[{user}] {txt}\n -> {reply}")
        await self.send_chat(reply)
        await speak(reply)

async def main():
    bot = TwitchChat()
    await bot.connect()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())




