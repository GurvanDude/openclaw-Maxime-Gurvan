import csv
import json
import os
import sqlite3


class Store:
    BACKENDS = ('csv', 'sqlite', 'json')

    def __init__(self, backend: str, path: str):
        if backend not in self.BACKENDS:
            raise ValueError(f'Backend inconnu: {backend}')
        self.backend = backend
        self.path = path
        dossier = os.path.dirname(path)
        if dossier:
            os.makedirs(dossier, exist_ok=True)

    def save(self, items: list[dict]) -> int:
        """Persiste les items. Retourne le nombre d'items inseres (hors doublons)."""
        if not items:
            return 0

        champs = list(items[0].keys())

        if self.backend == "csv":
            nouveau = not os.path.exists(self.path)
            with open(self.path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
                if nouveau:
                    writer.writeheader()
                writer.writerows(items)
            return len(items)

        if self.backend == "sqlite":
            colonnes = ", ".join(f"{c} TEXT" for c in champs)
            unique = ", UNIQUE(url)" if "url" in champs else ""
            insere = 0
            cx = sqlite3.connect(self.path)
            cx.execute(f"CREATE TABLE IF NOT EXISTS items ({colonnes}{unique})")
            for item in items:
                cx.execute(
                    f"INSERT OR IGNORE INTO items ({', '.join(champs)}) "
                    f"VALUES ({', '.join('?' * len(champs))})",
                    [item.get(c, "") for c in champs],
                )
                insere += cx.execute("SELECT changes()").fetchone()[0]
            cx.commit()
            cx.close()
            return insere

        anciens = []
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                anciens = json.load(f)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(anciens + items, f, ensure_ascii=False, indent=2)
        return len(items)

    def count(self) -> int:
        """Retourne le nombre total d'items dans le store."""
        if not os.path.exists(self.path):
            return 0

        if self.backend == "csv":
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                return len(list(csv.DictReader(f)))

        if self.backend == "sqlite":
            cx = sqlite3.connect(self.path)
            total = cx.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            cx.close()
            return total

        with open(self.path, "r", encoding="utf-8") as f:
            return len(json.load(f))

    def export_to(self, other_backend: str, path: str) -> int:
        """Exporte tous les items vers un autre backend. Retourne le nb exporte."""
        if not os.path.exists(self.path):
            return 0

        if self.backend == "csv":
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                items = list(csv.DictReader(f))
        elif self.backend == "sqlite":
            cx = sqlite3.connect(self.path)
            cx.row_factory = sqlite3.Row
            lignes = cx.execute("SELECT * FROM items").fetchall()
            cx.close()
            items = [dict(ligne) for ligne in lignes]
        else:
            with open(self.path, "r", encoding="utf-8") as f:
                items = json.load(f)

        return Store(other_backend, path).save(items)
