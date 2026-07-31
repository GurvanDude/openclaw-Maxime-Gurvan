"""Tests unitaires pour dataharvest.config.Config."""

import json

import pytest
import yaml

from dataharvest.config import Config

VALID_CONFIG = {
    "url": "https://www.blogdumoderateur.com/",
    "pagination": {"pattern": "/page/{n}/", "start": 1, "max_pages": 10},
    "selectors": {
        "titre": "h2.post-title a",
        "url": "h2.post-title a",
        "date": "time[datetime]",
        "categorie": ".cat-links a",
    },
    "fetcher": {
        "delay": 1.5,
        "retries": 3,
        "timeout": 15,
        "user_agent": "DataHarvest/1.0",
    },
    "store": {"backend": "sqlite", "path": "output/articles.db"},
}


def _write_yaml(tmp_path, data, name="config.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_config_raises_filenotfound_on_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError):
        Config(missing)


def test_config_raises_valueerror_on_missing_required_key(tmp_path):
    incomplete = json.loads(json.dumps(VALID_CONFIG))
    del incomplete["fetcher"]
    path = _write_yaml(tmp_path, incomplete)

    with pytest.raises(ValueError):
        Config(path)


def test_config_raises_valueerror_on_missing_nested_key(tmp_path):
    incomplete = json.loads(json.dumps(VALID_CONFIG))
    del incomplete["pagination"]["max_pages"]
    path = _write_yaml(tmp_path, incomplete)

    with pytest.raises(ValueError):
        Config(path)


def test_config_loads_valid_yaml(tmp_path):
    path = _write_yaml(tmp_path, VALID_CONFIG)

    config = Config(path)

    assert config.url == "https://www.blogdumoderateur.com/"
    assert config.fetcher.delay == 1.5
    assert isinstance(config.fetcher.delay, float)


def test_config_selectors_is_a_dict(tmp_path):
    path = _write_yaml(tmp_path, VALID_CONFIG)

    config = Config(path)

    assert isinstance(config.selectors, dict)
    assert config.selectors["titre"] == "h2.post-title a"


def test_config_supports_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(VALID_CONFIG), encoding="utf-8")

    config = Config(path)

    assert config.store.backend == "sqlite"
    assert config.store.path == "output/articles.db"


def test_config_pagination_accessible_as_attributes(tmp_path):
    path = _write_yaml(tmp_path, VALID_CONFIG)

    config = Config(path)

    assert config.pagination.start == 1
    assert config.pagination.max_pages == 10


def test_config_pagination_pattern_can_be_null(tmp_path):
    data = json.loads(json.dumps(VALID_CONFIG))
    data["pagination"]["pattern"] = None
    path = _write_yaml(tmp_path, data)

    config = Config(path)

    assert config.pagination.pattern is None


def test_config_unsupported_extension_raises_valueerror(tmp_path):
    path = tmp_path / "config.txt"
    path.write_text("url: https://example.com", encoding="utf-8")

    with pytest.raises(ValueError):
        Config(path)
