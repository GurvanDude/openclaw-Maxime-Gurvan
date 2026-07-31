"""Chargement et validation de la configuration (YAML/JSON) pour DataHarvest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigSection:
    """Enveloppe un dict et expose ses cles en attributs (ex: config.fetcher.delay)."""

    def __init__(self, data: dict[str, Any]):
        self._data = dict(data or {})
        for key, value in self._data.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"ConfigSection({self._data!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConfigSection):
            return self._data == other._data
        return NotImplemented

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)


class Config:
    """Charge un fichier de configuration YAML ou JSON et expose ses valeurs.

    Usage:
        config = Config("configs/example_blog.yaml")
        config.url               # str
        config.pagination.start  # int (attribut)
        config.selectors         # dict
        config.fetcher.delay     # float
        config.store.backend     # str
    """

    REQUIRED_KEYS = (
        "url",
        "pagination.pattern",
        "pagination.start",
        "pagination.max_pages",
        "selectors",
        "fetcher.delay",
        "fetcher.retries",
        "fetcher.timeout",
        "fetcher.user_agent",
        "store.backend",
        "store.path",
    )

    def __init__(self, path: str | Path):
        self.path = Path(path)

        if not self.path.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable: {self.path}")

        raw = self._load_raw(self.path)
        self._validate(raw)

        self.url: str = raw["url"]
        self.pagination = ConfigSection(raw["pagination"])
        self.selectors: dict[str, Any] = dict(raw["selectors"])
        self.fetcher = ConfigSection(raw["fetcher"])
        self.store = ConfigSection(raw["store"])
        self._raw = raw

    @staticmethod
    def _load_raw(path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()

        with open(path, "r", encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                import yaml

                data = yaml.safe_load(f)
            elif suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(
                    f"Format de configuration non supporte: '{suffix}' "
                    "(extensions acceptees: .yaml, .yml, .json)"
                )

        if not isinstance(data, dict):
            raise ValueError(f"Le contenu de {path} doit etre un mapping (dict) valide.")

        return data

    @classmethod
    def _validate(cls, data: dict[str, Any]) -> None:
        missing = [key for key in cls.REQUIRED_KEYS if not cls._has_nested(data, key)]
        if missing:
            raise ValueError(
                "Cle(s) obligatoire(s) absente(s) de la configuration: " + ", ".join(missing)
            )

    @staticmethod
    def _has_nested(data: dict[str, Any], dotted_key: str) -> bool:
        node: Any = data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    def as_dict(self) -> dict[str, Any]:
        return self._raw

    def __repr__(self) -> str:
        return f"Config(path={self.path!r}, url={self.url!r})"
