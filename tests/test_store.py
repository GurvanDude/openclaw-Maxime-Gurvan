"""Tests unitaires pour dataharvest.store.Store."""

import csv
import json

import pytest

from dataharvest.store import Store

ITEMS = [
    {"titre": "Premier article", "url": "https://exemple.fr/1", "date": "2026-07-31"},
    {"titre": "Deuxieme article", "url": "https://exemple.fr/2", "date": "2026-07-30"},
]


def test_store_leve_valueerror_sur_backend_inconnu(tmp_path):
    with pytest.raises(ValueError):
        Store("xml", str(tmp_path / "sortie.xml"))


def test_save_json_cree_un_fichier_json_valide(tmp_path):
    chemin = tmp_path / "articles.json"
    store = Store("json", str(chemin))

    insere = store.save(ITEMS)

    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    assert insere == 2
    assert isinstance(contenu, list)
    assert contenu[0]["titre"] == "Premier article"


def test_save_sqlite_ne_duplique_pas_la_meme_url(tmp_path):
    store = Store("sqlite", str(tmp_path / "articles.db"))

    premier = store.save(ITEMS)
    second = store.save(ITEMS)

    assert premier == 2
    assert second == 0
    assert store.count() == 2


def test_save_csv_ecrit_l_entete_une_seule_fois(tmp_path):
    chemin = tmp_path / "articles.csv"
    store = Store("csv", str(chemin))

    store.save(ITEMS)
    store.save(ITEMS)

    with open(chemin, "r", encoding="utf-8", newline="") as f:
        lignes = list(csv.reader(f))

    assert lignes[0] == ["titre", "url", "date"]
    assert len(lignes) == 5
    assert store.count() == 4


def test_count_retourne_zero_si_le_fichier_n_existe_pas(tmp_path):
    store = Store("json", str(tmp_path / "vide.json"))

    assert store.count() == 0


def test_save_ne_fait_rien_sur_une_liste_vide(tmp_path):
    store = Store("json", str(tmp_path / "vide.json"))

    assert store.save([]) == 0


def test_export_to_transfere_tous_les_items(tmp_path):
    source = Store("sqlite", str(tmp_path / "articles.db"))
    source.save(ITEMS)
    cible_chemin = tmp_path / "articles.json"

    exporte = source.export_to("json", str(cible_chemin))

    assert exporte == 2
    assert Store("json", str(cible_chemin)).count() == 2


def test_export_to_convertit_csv_vers_sqlite(tmp_path):
    source = Store("csv", str(tmp_path / "articles.csv"))
    source.save(ITEMS)
    cible_chemin = tmp_path / "articles.db"

    exporte = source.export_to("sqlite", str(cible_chemin))

    assert exporte == 2
    assert Store("sqlite", str(cible_chemin)).count() == 2


def test_export_to_convertit_json_vers_csv(tmp_path):
    source = Store("json", str(tmp_path / "articles.json"))
    source.save(ITEMS)
    cible_chemin = tmp_path / "articles.csv"

    exporte = source.export_to("csv", str(cible_chemin))

    assert exporte == 2
    assert Store("csv", str(cible_chemin)).count() == 2


def test_export_to_retourne_zero_si_la_source_n_existe_pas(tmp_path):
    source = Store("json", str(tmp_path / "vide.json"))

    assert source.export_to("csv", str(tmp_path / "sortie.csv")) == 0


def test_save_json_conserve_les_items_precedents(tmp_path):
    chemin = tmp_path / "articles.json"
    store = Store("json", str(chemin))

    store.save(ITEMS)
    store.save([{"titre": "Troisieme", "url": "https://exemple.fr/3", "date": "2026-07-29"}])

    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    assert len(contenu) == 3
    assert store.count() == 3


def test_le_dossier_de_sortie_est_cree(tmp_path):
    chemin = tmp_path / "output" / "articles.json"

    Store("json", str(chemin))

    assert chemin.parent.exists()
