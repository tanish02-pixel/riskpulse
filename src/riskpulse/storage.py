import json
import sqlite3
import threading
from contextlib import contextmanager
from .util import now_iso


class Store:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            from pathlib import Path
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL, body TEXT NOT NULL, source TEXT NOT NULL,
                source_type TEXT NOT NULL, url TEXT, published_at TEXT NOT NULL,
                received_at TEXT NOT NULL, mode TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY, article_id INTEGER REFERENCES articles(id),
                ticker TEXT, event TEXT NOT NULL, sentiment REAL NOT NULL,
                impact INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS signals_ticker ON signals(ticker);
            CREATE INDEX IF NOT EXISTS articles_received ON articles(received_at);
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, mode TEXT NOT NULL,
                reason TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_article(self, article, signals, content_hash):
        with self.lock, self.connect() as conn:
            if conn.execute("SELECT id FROM articles WHERE fingerprint=?", (content_hash,)).fetchone():
                return None
            cursor = conn.execute("INSERT INTO articles(fingerprint,title,body,source,source_type,url,published_at,received_at,mode) VALUES(?,?,?,?,?,?,?,?,?)",
                (content_hash, article["title"], article.get("body", ""), article["source"],
                article["source_type"], article.get("url", ""), article["published_at"], now_iso(), article["mode"]))
            article_id = cursor.lastrowid
            ids = []
            for signal in signals:
                cursor = conn.execute("INSERT INTO signals(article_id,ticker,event,sentiment,impact,payload) VALUES(?,?,?,?,?,?)",
                    (article_id, signal["ticker"], signal["event_classification"], signal["sentiment_score"], signal["impact_score"], json.dumps(signal)))
                ids.append(cursor.lastrowid)
            return {"article_id": article_id, "signal_ids": ids}

    def has_fingerprint(self, value):
        with self.connect() as conn:
            return conn.execute("SELECT id FROM articles WHERE fingerprint=?", (value,)).fetchone() is not None

    def signals(self, mode="live", ticker=None, event=None, search=None, limit=500):
        sql = "SELECT s.id,s.payload,a.title,a.body,a.source,a.source_type,a.url,a.published_at,a.received_at,a.mode FROM signals s JOIN articles a ON a.id=s.article_id WHERE a.mode=?"
        args = [mode]
        if ticker:
            sql += " AND s.ticker=?"
            args.append(ticker)
        if event:
            sql += " AND s.event=?"
            args.append(event)
        if search:
            sql += " AND a.title LIKE ?"
            args.append("%" + search + "%")
        sql += " ORDER BY s.id DESC LIMIT ?"
        args.append(limit)
        with self.connect() as conn:
            return [{**json.loads(row["payload"]), **{k: row[k] for k in row.keys() if k != "payload"}} for row in conn.execute(sql, args)]

    def snapshot(self, mode, reason, payload):
        with self.lock, self.connect() as conn:
            cursor = conn.execute("INSERT INTO snapshots(created_at,mode,reason,payload) VALUES(?,?,?,?)", (now_iso(), mode, reason, json.dumps(payload)))
            return cursor.lastrowid

    def history(self, mode, limit=100):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM snapshots WHERE mode=? ORDER BY id DESC LIMIT ?", (mode, limit)).fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "mode": r["mode"], "reason": r["reason"], **json.loads(r["payload"])} for r in reversed(rows)]

    def current(self, mode, tickers):
        rows = self.history(mode, 1)
        return rows[-1]["after"] if rows else {ticker: 1 / len(tickers) for ticker in tickers}

    def settings(self, name, default=None):
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM settings WHERE id=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_settings(self, name, value):
        with self.lock, self.connect() as conn:
            conn.execute("INSERT INTO settings(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (name, json.dumps(value)))

    def set_source(self, name, value):
        with self.lock, self.connect() as conn:
            conn.execute("INSERT INTO sources(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (name, json.dumps(value)))

    def sources(self):
        with self.connect() as conn:
            return {row[0]: json.loads(row[1]) for row in conn.execute("SELECT id,payload FROM sources")}

    def reset_replay(self):
        with self.lock, self.connect() as conn:
            conn.execute("DELETE FROM signals WHERE article_id IN (SELECT id FROM articles WHERE mode='replay')")
            conn.execute("DELETE FROM articles WHERE mode='replay'")
            conn.execute("DELETE FROM snapshots WHERE mode='replay'")

    def counts(self, mode):
        with self.connect() as conn:
            articles = conn.execute("SELECT COUNT(*) FROM articles WHERE mode=?", (mode,)).fetchone()[0]
            signals = conn.execute("SELECT COUNT(*) FROM signals s JOIN articles a ON a.id=s.article_id WHERE a.mode=?", (mode,)).fetchone()[0]
        return {"articles": articles, "signals": signals}

