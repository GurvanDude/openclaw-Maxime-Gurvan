import argparse

from dataharvest.config import Config
from dataharvest.fetcher import Fetcher
from dataharvest.middleware import LoggingMiddleware, RetryMiddleware
from dataharvest.orchestrator import Orchestrator
from dataharvest.pipeline import PaginationPipeline
from dataharvest.store import Store


def backend_du_fichier(chemin: str) -> str:
    """Deduit le backend a utiliser depuis l'extension du fichier."""
    if chemin.endswith(".csv"):
        return "csv"
    if chemin.endswith(".json"):
        return "json"
    return "sqlite"


def main():
    parser = argparse.ArgumentParser(
        prog="dataharvest", description="Framework de scraping modulaire"
    )
    sous_commandes = parser.add_subparsers(dest="commande", required=True)

    crawl = sous_commandes.add_parser("crawl", help="Scrape un site decrit par une config")
    crawl.add_argument("--config", required=True, help="Chemin du fichier YAML ou JSON")
    crawl.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetche et parse la premiere page, affiche les items sans stocker",
    )

    export = sous_commandes.add_parser("export", help="Convertit un fichier vers un autre backend")
    export.add_argument("--from", dest="source", required=True, help="Fichier source")
    export.add_argument("--to", dest="cible", required=True, help="Fichier de destination")

    valider = sous_commandes.add_parser("validate", help="Verifie une config sans scraper")
    valider.add_argument("--config", required=True, help="Chemin du fichier YAML ou JSON")

    args = parser.parse_args()

    if args.commande == "export":
        source = Store(backend_du_fichier(args.source), args.source)
        nombre = source.export_to(backend_du_fichier(args.cible), args.cible)
        print(f"{nombre} items exportes vers {args.cible}")
        return 0

    try:
        config = Config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Config invalide : {e}")
        return 1

    if args.commande == "validate":
        print(f"Config valide : {args.config}")
        print(f"  url        : {config.url}")
        print(f"  selecteurs : {', '.join(config.selectors)}")
        print(f"  pagination : {config.pagination.pattern} (max {config.pagination.max_pages})")
        print(f"  sortie     : {config.store.backend} -> {config.store.path}")
        return 0

    if args.dry_run:
        fetcher = Fetcher(config, middlewares=[LoggingMiddleware(), RetryMiddleware(config)])
        pipeline = PaginationPipeline(config.selectors, config.pagination)
        items = pipeline.process(fetcher.fetch(config.url), config.url)
        print(f"{len(items)} items trouves sur la premiere page, rien n'est stocke")
        for item in items:
            print(item)
        return 0

    rapport = Orchestrator(config).run()
    for cle, valeur in rapport.items():
        print(f"{cle} : {valeur}")
    return 0
