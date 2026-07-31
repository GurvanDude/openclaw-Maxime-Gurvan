import time
import requests

from dataharvest.middleware import BaseMiddleware


class FetchError(Exception):
    """Levee quand le telechargement echoue apres toutes les tentatives."""


class Fetcher:
    def __init__(self, config: Config, middlewares: list[BaseMiddleware] = None):
        self.config = config
        self.middlewares = middlewares or []
        self.headers = {"User-Agent": config.fetcher.user_agent}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch(self, url: str) -> str:
        """Retourne le HTML ou leve une exception apres epuisement des retries."""
        for attempt in range(self.config.fetcher.retries + 1):
            url_appel = url
            headers = dict(self.headers)
            for middleware in self.middlewares:
                url_appel, headers = middleware.process_request(url_appel, headers)

            try:
                response = self.session.get(
                    url_appel, headers=headers, timeout=self.config.fetcher.timeout
                )
            except requests.RequestException as e:
                print(f"Erreur reseau tentative {attempt + 1} : {e}")
                time.sleep(2 ** attempt)
                continue

            for middleware in self.middlewares:
                response = middleware.process_response(response)
                if response is None:
                    break  # un middleware demande de refaire la requete

            if response is not None:
                if response.status_code == 200:
                    return response.text
                print(f"Code {response.status_code} definitif sur {url}")
                break

        raise FetchError(f"Echec apres {self.config.fetcher.retries + 1} tentatives : {url}")

    def fetch_all(self, urls: list[str]) -> list[str]:
        """Fetche une liste d'URLs en respectant le delay entre chaque."""
        pages = []
        for url in urls:
            pages.append(self.fetch(url))
            time.sleep(self.config.fetcher.delay)
        return pages
