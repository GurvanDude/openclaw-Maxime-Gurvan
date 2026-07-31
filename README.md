# DataHarvest

Mini-framework de scraping modulaire et configurable.

Projet realise par Gurvan Godin et Maxime Danino.
Mastere Dev, Data & IA, 4eme annee, IPSSI Nice.

DataHarvest scrape n'importe quel site HTML statique a partir d'un simple fichier
de configuration. Ajouter un site ne demande aucune ligne de code, seulement un
nouveau fichier YAML dans `configs/`.

## Installation

```
git clone https://github.com/GurvanDude/openclaw-Maxime-Gurvan.git
cd openclaw-Maxime-Gurvan
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Sous Linux ou macOS, remplacer la ligne d'activation par `source .venv/bin/activate`.

## Utilisation

Trois sous-commandes sont disponibles.

```
python -m dataharvest crawl --config configs/books_toscrape.yaml
python -m dataharvest crawl --config configs/books_toscrape.yaml --dry-run
python -m dataharvest export --from output/articles.db --to output/articles.csv
python -m dataharvest validate --config configs/books_toscrape.yaml
```

`validate` ne fait aucune requete reseau. Il ouvre le fichier de configuration,
verifie que les cles obligatoires sont presentes et affiche un resume.

`crawl --dry-run` telecharge et analyse uniquement la premiere page, affiche les
items extraits et n'ecrit rien. C'est la commande a utiliser pour mettre au point
des selecteurs CSS.

`crawl` pagine jusqu'a `max_pages`, valide les items, les stocke et affiche un
rapport de session.

```
pages_scrapees : 5
items_trouves : 75
items_valides : 75
items_rejetes : 0
items_stockes : 75
duree_secondes : 8.42
```

`export` convertit un fichier de sortie vers un autre backend. Le format est
deduit de l'extension, `.csv`, `.json` ou `.db`.

## Architecture

Cinq composants independants, chacun dans son module. L'Orchestrator est le seul
a connaitre les autres, et il les recoit ou les construit par injection dans son
constructeur, jamais par import croise.

### Diagramme du flux de donnees

```
Config (YAML / JSON)
   |
   v
Orchestrator
   |-- Fetcher [+ chaine de middlewares] --> HTML brut
   |-- Pipeline.process(html) ------------> list[dict]
   |-- Validator.validate(items) ---------> (valides, rejetes)
   '-- Store.save(items) -----------------> csv / sqlite / json
```

### Diagramme de la chaine de middlewares

La chaine s'intercale entre le Fetcher et le reseau, sans que le Fetcher ait
besoin de connaitre le detail de chaque middleware.

```
fetch(url)
   |
   |-- LoggingMiddleware.process_request  --> [GET url]
   |-- RetryMiddleware.process_request
   |
   v  requests.Session().get(...)
   |
   |-- LoggingMiddleware.process_response --> [200 OK - 0.53s]
   '-- RetryMiddleware.process_response
          |
          '-- code 429 ou 5xx : attend base * (2 ** attempt)
              puis retourne None, ce qui relance la requete
```

| Module | Role |
| --- | --- |
| `config.py` | Charge un YAML ou un JSON, valide les 11 cles obligatoires, expose les valeurs en attributs |
| `middleware.py` | `BaseMiddleware` abstrait, plus le logging et le retry a backoff exponentiel |
| `fetcher.py` | Telechargement HTTP via `requests.Session`, traverse la chaine de middlewares, leve `FetchError` |
| `pipeline.py` | `BasePipeline` abstrait, `GenericPipeline` par selecteurs CSS, `PaginationPipeline` pour l'enchainement des pages |
| `validator.py` | Filtre les items sur les champs obligatoires, la validite de l'URL et les longueurs minimales |
| `store.py` | Persistance en csv, sqlite ou json, et conversion entre les trois via `export_to()` |
| `orchestrator.py` | Assemble le tout, pagine, et retourne le rapport de session |
| `app.py` | Interface en ligne de commande avec argparse |

Les choix de conception sont detailles dans le rapport technique,
[DataHarvest_Rapport_MaxMag.pdf](DataHarvest_Rapport_MaxMag.pdf).

## Configuration

Chaque site a son fichier dans `configs/`. Toutes les cles ci-dessous sont
obligatoires, `Config` leve une `ValueError` explicite si l'une manque.

```yaml
url: https://quotes.toscrape.com/
pagination:
  pattern: /page/{n}/     # null si le site n'est pas pagine
  start: 1
  max_pages: 5
selectors:
  titre: .quote span.text
  url: .quote > span > a
  auteur: .quote small.author
fetcher:
  delay: 1.0              # secondes entre deux pages
  retries: 3
  timeout: 15
  user_agent: DataHarvest/1.0 (+contact@ipssi.fr)
store:
  backend: json           # csv, sqlite ou json
  path: output/quotes_toscrape.json
```

Les noms de champs sous `selectors` sont libres et deviennent les colonnes du
fichier de sortie. Deux d'entre eux ont un traitement particulier. Le champ
`url` recupere le `href` du lien et le transforme en URL absolue. Le champ
`titre` est, avec `url`, l'un des deux champs obligatoires que le Validator
exige pour accepter un item.

Point important pour ecrire des selecteurs. Chaque selecteur est applique
separement sur la page entiere, puis les resultats sont alignes par position.
Tous les selecteurs d'une meme configuration doivent donc renvoyer le meme
nombre d'elements, sinon les champs se decalent d'une ligne a l'autre. En
pratique, il faut les prefixer par le conteneur commun, par exemple
`article h3.entry-title` plutot que `h3.entry-title`.

## Les 5 sites

| Site | Niveau | Champs extraits | Sortie |
| --- | --- | --- | --- |
| books.toscrape.com | 1 | titre, url, prix, disponibilite, categorie | `output/books_toscrape.csv` |
| quotes.toscrape.com | 1 | titre, url, auteur, tags | `output/quotes_toscrape.json` |
| fr.wikipedia.org | 2 | titre, url, rang, population | `output/wikipedia_population.db` |
| data.gouv.fr | 2 | titre, url, organisation | `output/data_gouv.csv` |
| blogdumoderateur.com | 3 | titre, url, date, categorie, chapeau | `output/blogdumoderateur.db` |

Trois niveaux de difficulte sont couverts, pour deux demandes au minimum. Les
trois backends de stockage sont utilises au moins une fois.

Le dossier `output/` n'existe pas dans le depot. Il est cree automatiquement au
premier `crawl`, et les fichiers de sortie sont generes au fur et a mesure des
lancements. Il est ignore par git pour ne pas versionner des donnees qui
changent a chaque execution.

Les deux configurations `example_blog.yaml` et `example_news.yaml` viennent du
sujet et sont conservees a titre d'exemple. Leurs selecteurs ne correspondent
plus au HTML actuel de ces deux sites, qui ont ete redesignes depuis. La
configuration `blogdumoderateur.yaml` est la version corrigee et fonctionnelle
pour ce site.

## Tests

```
pytest --tb=short -v
pytest --cov=dataharvest --cov-report=term-missing -v
pytest -m "not integration" -v
```

Resultat de `pytest --cov=dataharvest --cov-report=term-missing -v`.

```
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\...\openclaw-Maxime-Gurvan
configfile: pytest.ini
plugins: cov-7.1.0
collected 57 items

Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
dataharvest\__init__.py           1      0   100%
dataharvest\__main__.py           3      3     0%   1-5
dataharvest\app.py               54     54     0%   1-75
dataharvest\config.py            61      8    87%   19, 22-24, 27, 90, 112, 115
dataharvest\fetcher.py           39      0   100%
dataharvest\middleware.py        35      0   100%
dataharvest\orchestrator.py      38      0   100%
dataharvest\pipeline.py          83      1    99%   108
dataharvest\store.py             73      0   100%
dataharvest\validator.py         32      0   100%
-----------------------------------------------------------
TOTAL                           419     66    84%

57 passed in 3.86s
```

`app.py` et `__main__.py` ne sont pas couverts par les tests unitaires. Ce sont
les deux modules d'interface, ils se contentent de lire les arguments et
d'appeler les composants deja testes. Les quatre sous-commandes ont ete
verifiees a la main sur les 5 sites.

Le test de bout en bout de `test_integration.py` a besoin d'une connexion
internet puisqu'il scrape un vrai site. Il porte le marqueur `integration` et
s'exclut avec `pytest -m "not integration"`.

Les tests unitaires ne font aucune requete reseau. Ils remplacent l'objet
concerne par un double, `FausseSession` pour le Fetcher et `FauxFetcher` pour
l'Orchestrator, ce qui rend les resultats deterministes et instantanes.

## Structure du depot

```
openclaw-Maxime-Gurvan/
|- dataharvest/
|  |- __init__.py          version = '1.0.0'
|  |- __main__.py          point d'entree de python -m dataharvest
|  |- config.py            chargement YAML / JSON
|  |- middleware.py        BaseMiddleware, Logging, Retry
|  |- fetcher.py           HTTP avec chaine de middlewares
|  |- pipeline.py          BasePipeline (ABC) + implementations
|  |- validator.py         validation des items
|  |- store.py             backends csv / sqlite / json
|  |- orchestrator.py      chef d'orchestre
|  '- app.py               CLI argparse
|- tests/
|  |- test_config.py
|  |- test_fetcher.py
|  |- test_pipeline.py
|  |- test_validator.py
|  |- test_store.py
|  '- test_integration.py
|- configs/                un fichier YAML par site
|- output/                 genere au premier crawl, ignore par git
|- README.md
|- rapport_technique.pdf   rapport technique de 10 a 15 pages
|- pytest.ini
|- requirements.txt
'- .gitignore
```


## Repartition des taches

| | Gurvan Godin | Maxime Danino |
| --- | --- | --- |
| Sprint 1 | Config | BaseMiddleware, LoggingMiddleware, RetryMiddleware, Fetcher |
| Sprint 2 | GenericPipeline, PaginationPipeline | Validator |
| Sprint 3 | Store et `export_to()` | Store et `export_to()` |
| Sprint 4 | | Orchestrator et CLI |
| Configs | les 5 fichiers de sites | correction de `blogdumoderateur.yaml`, test des 5 configs et des sous-commandes |
| Tests | `test_config.py`, `test_pipeline.py`, relecture des fichiers de tests | `test_fetcher.py`, `test_validator.py`, `test_store.py`, `test_integration.py` |
| Documentation | rapport technique | README |

Le detail est visible dans `git log`.
