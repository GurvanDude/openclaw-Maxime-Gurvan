import time
from abc import ABC, abstractmethod


class BaseMiddleware(ABC):
    @abstractmethod
    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        """Retourne (url, headers) potentiellement modifies."""

    @abstractmethod
    def process_response(self, response) -> object:
        """Retourne la response potentiellement transformee."""


class LoggingMiddleware(BaseMiddleware):
    def __init__(self):
        self.depart = 0.0

    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        print(f"[GET {url}]")
        self.depart = time.perf_counter()
        return url, headers

    def process_response(self, response) -> object:
        duree = time.perf_counter() - self.depart
        print(f"[{response.status_code} {response.reason} - {duree:.2f}s]")
        return response


class RetryMiddleware(BaseMiddleware):
    CODES = (429, 500, 502, 503, 504)

    def __init__(self, config, base: float = 1.0):
        self.max_retries = config.fetcher.retries
        self.base = base
        self.attempt = 0

    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        return url, headers

    def process_response(self, response) -> object:
        if response.status_code in self.CODES and self.attempt < self.max_retries:
            delai = self.base * (2 ** self.attempt)
            print(f"Code {response.status_code} - nouvelle tentative dans {delai}s")
            time.sleep(delai)
            self.attempt += 1
            return None  # None = le Fetcher doit refaire la requete
        self.attempt = 0
        return response
