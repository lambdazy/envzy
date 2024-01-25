from __future__ import annotations

import sys
from pathlib import Path

import pytest

from envzy.classify import ModuleClassifier
from envzy.packages import PypiDistribution, BrokenModules


@pytest.fixture(scope='function')
def classifier(pypi_index_url) -> ModuleClassifier:
    return ModuleClassifier(pypi_index_url=pypi_index_url, target_python=sys.version_info[:2])


def test_classify_six(classifier: ModuleClassifier, monkeypatch, site_packages: Path):
    import six

    monkeypatch.setattr(classifier, 'files_to_distributions', {})
    assert classifier.classify([six]) == frozenset([
        BrokenModules(
            name='packages_with_bad_path',
            modules_paths=(
                ('six', f'{site_packages}/six.py'),
            )
        )
    ])


@pytest.mark.vcr
def test_classify_deepspeed(
    classifier: ModuleClassifier,
    pypi_index_url: str,
) -> None:
    import deepspeed  # type: ignore

    assert classifier.classify([deepspeed]) == frozenset({
        PypiDistribution(
            name='deepspeed',
            version='0.12.6',
            pypi_index_url=pypi_index_url,
            have_server_supported_tags=True
        )
    })
