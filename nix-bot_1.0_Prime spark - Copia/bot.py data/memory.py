# memory.py — memória simples com SQLite (fatos, histórico e contexto global)
import sqlite3, time
from typing import List, Optional

# ===== Memória por usuário (fatos + log) =====
SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user TEXT NOT NULL,
  fact TEXT NOT NULL,
  ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user TEXT NOT NULL,
  msg TEXT NOT NULL,
  reply TEXT,
  ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_user_ts ON facts(user, ts);
CREATE INDEX IF NOT EXISTS idx_log_user_ts   ON log(user, ts);
"""

# ===== Memória global (curto prazo do chat) =====
GLOBAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS chatlog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user TEXT NOT NULL,
  msg  TEXT NOT NULL,
  ts   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chatlog_ts ON chatlog(ts);
"""

class Memory:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.executescript(GLOBAL_SCHEMA)
        self.conn.commit()

    # --------- Fatos por usuário ---------
    def remember_fact(self, user: str, fact: str):
        self.conn.execute(
            "INSERT INTO facts(user,fact,ts) VALUES(?,?,?)",
            (user.lower(), fact.strip(), int(time.time()))
        )
        self.conn.commit()

    def forget_fact(self, user: str, text_like: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM facts WHERE user=? AND fact LIKE ?",
            (user.lower(), f"%{text_like}%")
        )
        self.conn.commit()
        return cur.rowcount

    def forget_all(self, user: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM facts WHERE user=?",
            (user.lower(),)
        )
        self.conn.commit()
        return cur.rowcount

    def list_facts(self, user: str, limit: int = 12) -> List[str]:
        cur = self.conn.execute(
            "SELECT fact FROM facts WHERE user=? ORDER BY ts DESC LIMIT ?",
            (user.lower(), limit)
        )
        return [r[0] for r in cur.fetchall()]

    # --------- Log por usuário ---------
    def save_interaction(self, user: str, msg: str, reply: Optional[str]):
        self.conn.execute(
            "INSERT INTO log(user,msg,reply,ts) VALUES(?,?,?,?)",
            (user.lower(), msg, reply, int(time.time()))
        )
        self.conn.commit()

    def recent_summary(self, user: str, limit: int = 6) -> str:
        """Resumo curtinho para dar contexto ao LLM (ordem cronológica)."""
        cur = self.conn.execute(
            "SELECT msg,reply FROM log WHERE user=? ORDER BY ts DESC LIMIT ?",
            (user.lower(), limit)
        )
        items = cur.fetchall()
        if not items:
            return ""
        lines = []
        for m, r in items[::-1]:
            lines.append(f"User: {m.strip()}")
            if r:
                lines.append(f"Nix: {r.strip()}")
        return "\n".join(lines)

    # --------- Memória Global (curto prazo do chat) ---------
    def _ensure_global(self):
        self.conn.executescript(GLOBAL_SCHEMA)
        self.conn.commit()

    def save_global(self, user: str, msg: str, max_rows: int = 200):
        self._ensure_global()
        self.conn.execute(
            "INSERT INTO chatlog(user,msg,ts) VALUES(?,?,?)",
            (user.lower(), msg.strip(), int(time.time()))
        )
        self.conn.execute(
            "DELETE FROM chatlog WHERE id NOT IN (SELECT id FROM chatlog ORDER BY ts DESC LIMIT ?)",
            (max_rows,)
        )
        self.conn.commit()

    def recent_global(self, limit: int = 14) -> str:
        self._ensure_global()
        cur = self.conn.execute(
            "SELECT user,msg FROM chatlog ORDER BY ts DESC LIMIT ?",
            (limit,)
        )
        rows = cur.fetchall()[::-1]
        if not rows:
            return ""
        lines = []
        for u, m in rows:
            m = m.strip()
            if len(m) > 140:
                m = m[:140] + "…"
            lines.append(f"{u}: {m}")
        return "\n".join(lines)

    # --------- Heurística simples para extrair preferências ---------
    def auto_extract_and_store(self, user: str, msg: str):
        text = msg.lower()
        hits = []
        if "eu gosto de" in text:
            hits.append("gosta de " + text.split("eu gosto de", 1)[1].strip())
        if "meu jogo favorito é" in text:
            hits.append("jogo favorito: " + text.split("meu jogo favorito é", 1)[1].strip())
        if "sou main" in text:
            hits.append("é main " + text.split("sou main", 1)[1].strip())
        for h in hits:
            self.remember_fact(user, h)



