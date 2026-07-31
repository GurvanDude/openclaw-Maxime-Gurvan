class BasePipeline(ABC):
    @abstractmethod
    def process(self, html: str) -> list[dict]:
        """Retourne TOUJOURS une liste, jamais None."""

    @abstractmethod
    def next_page_url(self, html: str, current_url: str) -> str | None:
        """Retourne l'URL de la page suivante ou None si fin."""
