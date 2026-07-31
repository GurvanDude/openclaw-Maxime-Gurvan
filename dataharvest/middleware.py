from abc import ABC, abstractmethod


class BaseMiddleware(ABC):
    @abstractmethod
    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        """Retourne (url, headers) potentiellement modifies."""

    @abstractmethod
    def process_response(self, response) -> object:
        """Retourne la response potentiellement transformee."""
