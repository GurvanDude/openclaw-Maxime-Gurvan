"""Tests unitaires pour dataharvest.validator.Validator."""

import logging

from dataharvest.validator import Validator


def test_validate_accepte_un_item_complet():
    validator = Validator(required_fields=["titre", "url"])

    valides, rejetes = validator.validate(
        [{"titre": "Un article", "url": "https://exemple.fr/article"}]
    )

    assert len(valides) == 1
    assert rejetes == []


def test_validate_rejette_un_item_sans_champ_obligatoire():
    validator = Validator(required_fields=["titre", "url"])

    valides, rejetes = validator.validate([{"url": "https://exemple.fr/article"}])

    assert valides == []
    assert len(rejetes) == 1


def test_validate_rejette_un_champ_obligatoire_vide():
    validator = Validator(required_fields=["titre", "url"])

    valides, rejetes = validator.validate(
        [{"titre": "", "url": "https://exemple.fr/article"}]
    )

    assert valides == []
    assert len(rejetes) == 1


def test_validate_rejette_une_url_invalide():
    validator = Validator(required_fields=["titre", "url"])

    valides, rejetes = validator.validate([{"titre": "Un article", "url": "/article/12"}])

    assert valides == []
    assert len(rejetes) == 1


def test_validate_rejette_un_titre_trop_court():
    validator = Validator(required_fields=["titre"], min_lengths={"titre": 5})

    valides, rejetes = validator.validate(
        [{"titre": "Abc"}, {"titre": "Un titre assez long"}]
    )

    assert len(valides) == 1
    assert len(rejetes) == 1
    assert valides[0]["titre"] == "Un titre assez long"


def test_validate_ne_modifie_pas_les_items():
    validator = Validator(required_fields=["titre"])
    item = {"titre": "Un article", "url": "https://exemple.fr/article"}

    validator.validate([item])

    assert item == {"titre": "Un article", "url": "https://exemple.fr/article"}


def test_validate_logue_un_warning_par_item_rejete(caplog):
    validator = Validator(required_fields=["titre"])

    with caplog.at_level(logging.WARNING):
        validator.validate([{"titre": ""}, {"titre": ""}])

    assert len(caplog.records) == 2
    assert caplog.records[0].levelname == "WARNING"


def test_is_valid_url():
    validator = Validator(required_fields=["url"])

    assert validator.is_valid_url("https://exemple.fr/page") is True
    assert validator.is_valid_url("http://exemple.fr") is True
    assert validator.is_valid_url("/page/2") is False
    assert validator.is_valid_url("ftp://exemple.fr") is False
    assert validator.is_valid_url("https://") is False
