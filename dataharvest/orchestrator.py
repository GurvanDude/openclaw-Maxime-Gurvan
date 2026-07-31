import time

from dataharvest.fetcher import Fetcher, FetchError
from dataharvest.middleware import LoggingMiddleware, RetryMiddleware
from dataharvest.pipeline import PaginationPipeline
from dataharvest.store import Store
from dataharvest.validator import Validator


class Orchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.fetcher    = Fetcher(config, middlewares=[LoggingMiddleware(),
                                                       RetryMiddleware(config)])
        self.pipeline   = PaginationPipeline(config.selectors, config.pagination)
        self.validator  = Validator(required_fields=['titre', 'url'])
        self.store      = Store(config.store.backend, config.store.path)

    def run(self) -> dict:
        """Lance le scraping complet. Retourne un rapport de session."""
        self.debut = time.perf_counter()
        pages = []
        valides = []
        rejetes = []
        stockes = 0
        url = self.config.url

        while url:
            try:
                html = self.fetcher.fetch(url)
            except FetchError as e:
                print(f"Arret de la pagination : {e}")
                break

            pages.append(html)
            items = self.pipeline.process(html, url)
            page_valides, page_rejetes = self.validator.validate(items)
            valides.extend(page_valides)
            rejetes.extend(page_rejetes)
            stockes += self.store.save(page_valides)

            url = self.pipeline.next_page_url(html, url)
            if url:
                time.sleep(self.config.fetcher.delay)

        return self._build_report(pages, valides, rejetes, stockes)

    def _build_report(self, fetched, valid, rejected, stored) -> dict:
        """Construit le rapport JSON de la session."""
        return {
            "pages_scrapees": len(fetched),
            "items_trouves": len(valid) + len(rejected),
            "items_valides": len(valid),
            "items_rejetes": len(rejected),
            "items_stockes": stored,
            "duree_secondes": round(time.perf_counter() - self.debut, 2),
        }
