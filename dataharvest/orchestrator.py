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

    def _build_report(self, fetched, valid, rejected, stored) -> dict:
        """Construit le rapport JSON de la session."""
