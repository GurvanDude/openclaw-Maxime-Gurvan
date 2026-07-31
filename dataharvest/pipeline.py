"""Pipeline -- extraction des donnees structurees depuis le HTML brut."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from bs4 import BeautifulSoup


class BasePipeline(ABC):
    @abstractmethod
    def process(self, html: str) -> list[dict]:
        """Retourne TOUJOURS une liste, jamais None."""

    @abstractmethod
    def next_page_url(self, html: str, current_url: str) -> str | None:
        """Retourne l'URL de la page suivante ou None si fin."""


class GenericPipeline(BasePipeline):
    """Extrait des items depuis du HTML en utilisant des selecteurs CSS configurables.

    Les selecteurs ne sont jamais codes en dur : ils viennent du dict `selectors`
    fourni au constructeur (ex: {"titre": "h2.post-title a", "date": "time[datetime]"}).
    """

    def __init__(self, selectors: dict):
        self.selectors = dict(selectors or {})

    def process(self, html: str, base_url: str | None = None) -> list[dict]:
        """Retourne la liste des items extraits. Ne leve jamais d'exception.

        Chaque selecteur est applique independamment sur le document. Le nombre
        d'items correspond au selecteur qui trouve le plus de correspondances ;
        les selecteurs qui n'ont pas assez de matchs (ou aucun) se voient
        attribuer une chaine vide pour les index manquants.
        """
        if not html or not self.selectors:
            return []

        soup = BeautifulSoup(html, "lxml")

        matches = {field: soup.select(css) for field, css in self.selectors.items()}
        nb_items = max((len(elements) for elements in matches.values()), default=0)

        items: list[dict] = []
        for index in range(nb_items):
            item = {
                field: self._extract_value(
                    field, elements[index] if index < len(elements) else None, base_url
                )
                for field, elements in matches.items()
            }
            items.append(item)

        return items

    @staticmethod
    def _extract_value(field: str, element, base_url: str | None) -> str:
        """Extrait une valeur texte/attribut d'un element BeautifulSoup, sans jamais lever.

        Le champ nomme 'url' est traite specifiquement (on veut le href, pas le
        texte) -- c'est une convention du schema de config, pas un selecteur
        code en dur. Les autres champs sont extraits generiquement : attribut
        'datetime' si present (balises <time>), sinon le texte de l'element.
        """
        if element is None:
            return ""

        if field == "url":
            link = element if (element.name == "a" and element.has_attr("href")) else element.find("a")
            href = link.get("href", "") if link else ""
            return GenericPipeline._resolve_url(href, base_url)

        if element.has_attr("datetime"):
            return element["datetime"]

        return element.get_text(strip=True)

    @staticmethod
    def _resolve_url(href: str, base_url: str | None) -> str:
        if not href:
            return ""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if base_url:
            return urljoin(base_url, href)
        return href

    def next_page_url(self, html: str, current_url: str) -> str | None:
        """GenericPipeline ne pagine pas -- reserve a PaginationPipeline."""
        return None


class PaginationPipeline(GenericPipeline):
    """GenericPipeline + gestion de la pagination selon config.pagination.

    pagination_config expose (en attributs, cf Config/ConfigSection) :
        - pattern    : ex '/page/{n}/', ou None si le site n'est pas paginable
        - start      : numero de la premiere page (generalement 1)
        - max_pages  : nombre maximum de pages a parcourir

    Le pattern de pagination est reconstruit a partir de current_url a chaque
    appel (plutot que stocke une seule fois a la construction) : cela permet de
    gerer correctement le cas ou current_url contient deja un segment de
    pagination (ex: on vient de fetcher /page/2/ et on veut /page/3/).
    """

    def __init__(self, selectors: dict, pagination_config):
        super().__init__(selectors)
        self.pagination_config = pagination_config
        self._pattern = getattr(pagination_config, "pattern", None)
        self._start = getattr(pagination_config, "start", 1) or 1
        self._max_pages = getattr(pagination_config, "max_pages", 1) or 1
        self._pages_seen = 0

    def next_page_url(self, html: str, current_url: str) -> str | None:
        """Retourne l'URL de la page suivante, ou None si la pagination est finie."""
        self._pages_seen += 1
        current_page_number = self._start + self._pages_seen - 1

        if not self._pattern:
            return None

        if current_page_number >= self._start + self._max_pages - 1:
            return None

        if len(self.process(html)) == 0:
            return None

        next_number = current_page_number + 1
        return self._build_next_url(current_url, next_number)

    def _build_next_url(self, current_url: str, next_number: int) -> str:
        """Construit l'URL de la page `next_number` a partir de current_url et du pattern."""
        page_regex = re.escape(self._pattern).replace(r"\{n\}", r"\d+")
        next_suffix = self._pattern.replace("{n}", str(next_number))

        match = re.search(page_regex, current_url)
        if match:
            return current_url[: match.start()] + next_suffix + current_url[match.end() :]

        return current_url.rstrip("/") + next_suffix
