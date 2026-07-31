import json
import os

import pytest
import yaml

from dataharvest.config import Config
from dataharvest.fetcher import FetchError
from dataharvest.orchestrator import Orchestrator

CLES_DU_RAPPORT = [
    "pages_scrapees",
    "items_trouves",
    "items_valides",
    "items_rejetes",
    "items_stockes",
    "duree_secondes",
]

HTML = """
<html><body>
  <article><h2>Premier article</h2><a href="https://exemple.fr/1">lire</a></article>
  <article><h2>Deuxieme article</h2><a href="https://exemple.fr/2">lire</a></article>
</body></html>
"""


def ecrire_config(tmp_path, pattern=None, max_pages=1):
    data = {
        "url": "https://exemple.fr/",
        "pagination": {"pattern": pattern, "start": 1, "max_pages": max_pages},
        "selectors": {"titre": "article h2", "url": "article a"},
        "fetcher": {
            "delay": 0.01,
            "retries": 1,
            "timeout": 5,
            "user_agent": "DataHarvest/1.0 (+contact@ipssi.fr)",
        },
        "store": {"backend": "json", "path": str(tmp_path / "sortie.json")},
    }
    chemin = tmp_path / "config.yaml"
    chemin.write_text(yaml.safe_dump(data), encoding="utf-8")
    return Config(chemin)


class FauxFetcher:
    """Remplace le Fetcher pour tester l'Orchestrator sans passer par le reseau."""

    def __init__(self, html=HTML, erreur=None):
        self.html = html
        self.erreur = erreur
        self.appels = 0

    def fetch(self, url):
        self.appels += 1
        if self.erreur:
            raise self.erreur
        return self.html


def test_run_retourne_un_dict_avec_toutes_les_cles(tmp_path):
    orchestrator = Orchestrator(ecrire_config(tmp_path))
    orchestrator.fetcher = FauxFetcher()

    rapport = orchestrator.run()

    for cle in CLES_DU_RAPPORT:
        assert cle in rapport

    assert rapport["pages_scrapees"] == 1
    assert rapport["items_trouves"] == 2
    assert rapport["items_valides"] == 2
    assert rapport["items_rejetes"] == 0
    assert rapport["items_stockes"] == 2


def test_run_ecrit_bien_dans_le_store(tmp_path):
    config = ecrire_config(tmp_path)
    orchestrator = Orchestrator(config)
    orchestrator.fetcher = FauxFetcher()

    orchestrator.run()

    contenu = json.loads((tmp_path / "sortie.json").read_text(encoding="utf-8"))
    assert len(contenu) == 2
    assert contenu[0]["titre"] == "Premier article"


def test_run_pagine_jusqu_a_max_pages(tmp_path):
    config = ecrire_config(tmp_path, pattern="/page/{n}/", max_pages=2)
    orchestrator = Orchestrator(config)
    orchestrator.fetcher = FauxFetcher()

    rapport = orchestrator.run()

    assert orchestrator.fetcher.appels == 2
    assert rapport["pages_scrapees"] == 2
    assert rapport["items_trouves"] == 4


def test_run_rejette_les_items_sans_titre(tmp_path):
    orchestrator = Orchestrator(ecrire_config(tmp_path))
    orchestrator.fetcher = FauxFetcher(html="<article><a href='https://exemple.fr/1'>x</a></article>")

    rapport = orchestrator.run()

    assert rapport["items_valides"] == 0
    assert rapport["items_rejetes"] == 1
    assert rapport["items_stockes"] == 0


def test_run_s_arrete_proprement_si_le_fetch_echoue(tmp_path):
    orchestrator = Orchestrator(ecrire_config(tmp_path))
    orchestrator.fetcher = FauxFetcher(erreur=FetchError("echec"))

    rapport = orchestrator.run()

    assert rapport["pages_scrapees"] == 0
    assert rapport["items_stockes"] == 0


@pytest.mark.integration
def test_end_to_end_sur_le_vrai_site(tmp_path):
    fichier = str(tmp_path / "articles.db")
    config = Config("configs/blogdumoderateur.yaml")
    config.pagination.max_pages = 2
    config.store.path = fichier

    rapport = Orchestrator(config).run()

    assert rapport["items_stockes"] >= 5
    assert os.path.exists(fichier)
    assert os.path.getsize(fichier) > 0
