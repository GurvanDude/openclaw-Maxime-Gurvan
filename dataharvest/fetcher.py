class Fetcher:
    def __init__(self, config: Config, middlewares: list[BaseMiddleware] = None):
        ...

    def fetch(self, url: str) -> str:
        """Retourne le HTML ou leve une exception apres epuisement des retries."""

    def fetch_all(self, urls: list[str]) -> list[str]:
        """Fetche une liste d'URLs en respectant le delay entre chaque."""
