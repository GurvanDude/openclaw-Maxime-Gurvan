"""Tests unitaires pour dataharvest.fetcher.Fetcher."""

import pytest
import requests
import yaml

from dataharvest.config import Config
from dataharvest.fetcher import Fetcher, FetchError
from dataharvest.middleware import BaseMiddleware, RetryMiddleware


def ecrire_config(tmp_path, retries=2):
    data = {
        "url": "https://quotes.toscrape.com/",
        "pagination": {"pattern": "/page/{n}/", "start": 1, "max_pages": 2},
        "selectors": {"titre": "span.text", "url": "a"},
        "fetcher": {
            "delay": 0.1,
            "retries": retries,
            "timeout": 15,
            "user_agent": "DataHarvest/1.0 (+contact@ipssi.fr)",
        },
        "store": {"backend": "json", "path": "output/quotes.json"},
    }
    chemin = tmp_path / "config.yaml"
    chemin.write_text(yaml.safe_dump(data), encoding="utf-8")
    return Config(chemin)


@pytest.fixture
def config(tmp_path):
    return ecrire_config(tmp_path)


class FausseReponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.reason = "OK"
        self.text = text


class FausseSession:
    """Remplace requests.Session pour tester sans passer par le reseau."""

    def __init__(self, reponse=None, erreur=None):
        self.reponse = reponse
        self.erreur = erreur
        self.headers = {}
        self.appels = 0

    def get(self, url, headers=None, timeout=None):
        self.appels += 1
        if self.erreur:
            raise self.erreur
        return self.reponse


class MiddlewareCompteur(BaseMiddleware):
    """Middleware minimal qui compte les passages, pour verifier la chaine."""

    def __init__(self):
        self.requetes = 0
        self.reponses = 0

    def process_request(self, url, headers):
        self.requetes += 1
        return url, headers

    def process_response(self, response):
        self.reponses += 1
        return response


def test_fetch_retourne_un_html_non_vide(config):
    fetcher = Fetcher(config)

    html = fetcher.fetch("https://quotes.toscrape.com/")

    assert isinstance(html, str)
    assert len(html) > 0


def test_le_user_agent_vient_de_la_config(config):
    fetcher = Fetcher(config)

    assert fetcher.session.headers["User-Agent"] == "DataHarvest/1.0 (+contact@ipssi.fr)"


def test_fetch_leve_fetcherror_sur_un_code_erreur(config):
    fetcher = Fetcher(config)
    fetcher.session = FausseSession(FausseReponse(503))

    with pytest.raises(FetchError):
        fetcher.fetch("https://exemple.fr/")

    # sans RetryMiddleware personne ne demande de relance
    assert fetcher.session.appels == 1


def test_fetch_leve_fetcherror_apres_les_retries(config):
    fetcher = Fetcher(config, middlewares=[RetryMiddleware(config, base=0.01)])
    fetcher.session = FausseSession(FausseReponse(503))

    with pytest.raises(FetchError):
        fetcher.fetch("https://exemple.fr/")

    assert fetcher.session.appels == config.fetcher.retries + 1


def test_fetch_leve_fetcherror_si_le_reseau_tombe(tmp_path):
    config = ecrire_config(tmp_path, retries=0)
    fetcher = Fetcher(config)
    fetcher.session = FausseSession(erreur=requests.ConnectionError("pas de reseau"))

    with pytest.raises(FetchError):
        fetcher.fetch("https://exemple.fr/")

    assert fetcher.session.appels == 1


def test_fetch_passe_par_tous_les_middlewares(config):
    compteur = MiddlewareCompteur()
    fetcher = Fetcher(config, middlewares=[compteur])
    fetcher.session = FausseSession(FausseReponse(200, "<html></html>"))

    fetcher.fetch("https://exemple.fr/")

    assert compteur.requetes == 1
    assert compteur.reponses == 1


def test_fetch_all_retourne_une_page_par_url(config):
    fetcher = Fetcher(config)
    fetcher.session = FausseSession(FausseReponse(200, "<html></html>"))

    pages = fetcher.fetch_all(["https://exemple.fr/1", "https://exemple.fr/2"])

    assert len(pages) == 2
    assert fetcher.session.appels == 2
