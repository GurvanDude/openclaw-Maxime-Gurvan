import logging

logger = logging.getLogger(__name__)


class Validator:
    def __init__(self, required_fields: list[str], min_lengths: dict = None):
        self.required_fields = required_fields
        self.min_lengths = min_lengths or {}

    def validate(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        """Retourne (valides, rejetes)."""
        valides = []
        rejetes = []

        for item in items:
            raison = ""

            for champ in self.required_fields:
                if not item.get(champ):
                    raison = f"champ obligatoire vide ou absent ({champ})"
                    break

            if not raison and "url" in item and not self.is_valid_url(item["url"]):
                raison = f"url invalide ({item['url']})"

            if not raison:
                for champ, taille in self.min_lengths.items():
                    if len(item.get(champ, "")) < taille:
                        raison = f"{champ} plus court que {taille} caracteres"
                        break

            if raison:
                logger.warning(f"Item rejete, {raison} : {item}")
                rejetes.append(item)
            else:
                valides.append(item)

        return valides, rejetes

    def is_valid_url(self, url: str) -> bool:
        """True si l'URL commence par http(s):// et contient un domaine."""
        if not url.startswith(("http://", "https://")):
            return False
        domaine = url.split("//")[1].split("/")[0]
        return "." in domaine
