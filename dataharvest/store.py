class Store:
    BACKENDS = ('csv', 'sqlite', 'json')

    def __init__(self, backend: str, path: str):
        if backend not in self.BACKENDS:
            raise ValueError(f'Backend inconnu: {backend}')

    def save(self, items: list[dict]) -> int:
        """Persiste les items. Retourne le nombre d'items inseres (hors doublons)."""

    def count(self) -> int:
        """Retourne le nombre total d'items dans le store."""

    def export_to(self, other_backend: str, path: str) -> int:
        """Exporte tous les items vers un autre backend. Retourne le nb exporte."""
