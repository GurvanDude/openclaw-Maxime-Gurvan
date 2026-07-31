class Validator:
    def __init__(self, required_fields: list[str], min_lengths: dict = None):
        ...

    def validate(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        """Retourne (valides, rejetes)."""

    def is_valid_url(self, url: str) -> bool:
        """True si l'URL commence par http(s):// et contient un domaine."""
