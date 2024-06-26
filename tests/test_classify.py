from __future__ import annotations

import sys
import dataclasses
from pathlib import Path
from typing import Set

import pytest
from envzy.classify import ModuleClassifier
from envzy.packages import LocalPackage, PypiDistribution, LocalDistribution, BasePackage
from envzy.utils import Distribution


@pytest.fixture(scope='function')
def classifier(pypi_index_url) -> ModuleClassifier:
    return ModuleClassifier(pypi_index_url=pypi_index_url, target_python=sys.version_info[:2])


def test_classify_local_packages(
    with_test_modules,
    get_test_data_path,
    monkeypatch,
    classifier: ModuleClassifier,
) -> None:
    monkeypatch.syspath_prepend(get_test_data_path('namespace'))

    import modules_for_tests.level1.level1 as level1
    import modules_for_tests.foo as foo
    import empty_module

    # regular module
    assert classifier.classify([level1]) == frozenset([LocalPackage(
        name='modules_for_tests',
        paths=frozenset([str(get_test_data_path('modules_for_tests'))]),
        is_binary=False,
        console_scripts=frozenset(),
    )])

    # two modules within one namespace but different locations
    assert classifier.classify([level1, foo]) == frozenset([LocalPackage(
        name='modules_for_tests',
        paths=frozenset([
            str(get_test_data_path('modules_for_tests')),
            str(get_test_data_path('namespace', 'modules_for_tests')),
        ]),
        is_binary=False,
        console_scripts=frozenset(),
    )])

    # toplevel module without a package
    assert classifier.classify([empty_module]) == frozenset([LocalPackage(
        name='empty_module',
        paths=frozenset([str(get_test_data_path('empty_module.py'))]),
        is_binary=False,
        console_scripts=frozenset(),
    )])


@pytest.mark.vcr
def test_classify_pypi_packages(
    classifier: ModuleClassifier,
    pypi_index_url: str,
    env_prefix: Path,
    site_packages: Path
) -> None:
    import sample

    assert classifier.classify([sample]) == frozenset({
        PypiDistribution(
            name='sampleproject',
            version='3.0.0',
            pypi_index_url=pypi_index_url,
            have_server_supported_tags=True,
        ),
        LocalDistribution(
            name='lzy-test-project',
            paths=frozenset({
                f'{site_packages}/lzy_test_project',
                f'{site_packages}/lzy_test_project-3.0.0.dist-info'
            }),
            is_binary=False,
            version='3.0.0',
            bad_paths=frozenset(),
            console_scripts=frozenset({f'{env_prefix}/bin/lzy_test_project_bin'}),
        ),
    })

    @dataclasses.dataclass
    class MyDistribution:
        name: str
        version: str

    assert classifier._classify_distributions([  # type: ignore
        MyDistribution('tensorflow', '2.13.0')
    ], set()) == frozenset([
        PypiDistribution(
            name='tensorflow',
            version='2.13.0',
            pypi_index_url=pypi_index_url,
            have_server_supported_tags=True
        )
    ])

    assert classifier._classify_distributions([  # type: ignore
        MyDistribution('tensorflow-intel', '2.13.0')
    ], set()) == frozenset([
        PypiDistribution(
            name='tensorflow-intel',
            version='2.13.0',
            pypi_index_url=pypi_index_url,
            have_server_supported_tags=False
        )
    ])


@pytest.mark.vcr
def test_classify_local_distribution(
    classifier: ModuleClassifier,
    env_prefix: Path,
    site_packages: Path,
    pypi_index_url: str,
    monkeypatch,
) -> None:
    # NB: lzy_test_project located at test_data/lzy_test_project and gets installed by tox while
    # tox venv preparing
    import lzy_test_project.foo
    import lzy_test_project

    etalon = LocalDistribution(
        name='lzy-test-project',
        paths=frozenset({
            f'{site_packages}/lzy_test_project',
            f'{site_packages}/lzy_test_project-3.0.0.dist-info'
        }),
        is_binary=False,
        version='3.0.0',
        bad_paths=frozenset(),
        console_scripts=frozenset({f'{env_prefix}/bin/lzy_test_project_bin'}),
    )

    def classify(module) -> Set[BasePackage]:
        result = classifier.classify([module])

        return {p for p in result if p.name != 'sampleproject'}

    assert classify(lzy_test_project) == frozenset({etalon})
    assert classify(lzy_test_project.foo) == frozenset({dataclasses.replace(etalon, is_binary=True)})

    old_classify_distribution = classifier._classify_distribution
    meta_etalon = PypiDistribution(
        name='foo',
        version='bar',
        pypi_index_url='baz',
        have_server_supported_tags=True
    )

    def new_classify_distribution(self, distribution: Distribution, *args, **kwargs) -> BasePackage:
        if distribution.name == 'lzy-test-project-meta':
            return meta_etalon

        return old_classify_distribution(distribution, *args, **kwargs)

    monkeypatch.setattr(ModuleClassifier, '_classify_distribution', new_classify_distribution)
    patched_classifier = ModuleClassifier(pypi_index_url=pypi_index_url, target_python=sys.version_info[:2])

    # Because lzy-test-project is "found" at pypi (bless monkeypatch), we add meta-package
    # to result itself instead of adding it requirements
    assert patched_classifier.classify([lzy_test_project]) == frozenset({etalon, meta_etalon})


def test_classify_editable_distribution(classifier: ModuleClassifier, get_test_data_path) -> None:
    # NB: lzy_test_project_editable located at test_data/lzy_test_project_editable and gets installed by tox while
    # tox venv preparing
    import lzy_test_project_editable

    assert classifier.classify([lzy_test_project_editable]) == frozenset({
        LocalPackage(
            name='lzy_test_project_editable',
            paths=frozenset({
                f'{get_test_data_path()}/lzy_test_project_editable/src/lzy_test_project_editable'
            }),
            is_binary=False,
            console_scripts=frozenset(),
        )
    })


@pytest.mark.vcr
def test_classify_with_extra_index(pypi_index_url) -> None:
    classifier = ModuleClassifier(
        pypi_index_url=pypi_index_url,
        target_python=sys.version_info[:2],
        extra_index_urls=('https://download.pytorch.org/whl/cu118', )
    )

    @dataclasses.dataclass(frozen=True)
    class MyDistribution:
        name: str
        version: str

    assert classifier._classify_distributions({
        MyDistribution('tensorflow', '2.13.0'),  # type: ignore
        MyDistribution('torch', '2.1.1+cu118'),  # type: ignore
    }, set()) == frozenset([
        PypiDistribution(
            name='torch',
            version='2.1.1+cu118',
            pypi_index_url='https://download.pytorch.org/whl/cu118',
            have_server_supported_tags=True
        ),
        PypiDistribution(
            name='tensorflow',
            version='2.13.0',
            pypi_index_url='https://pypi.org/simple/',
            have_server_supported_tags=True
        ),
    ])

    assert classifier._classify_distributions({
        MyDistribution('tensorflow', '2.13.0'),  # type: ignore
        MyDistribution('torch', '2.1.1'),  # type: ignore
    }, set()) == frozenset([
        PypiDistribution(
            name='torch',
            version='2.1.1',
            pypi_index_url='https://pypi.org/simple/',
            have_server_supported_tags=True
        ),
        PypiDistribution(
            name='tensorflow',
            version='2.13.0',
            pypi_index_url='https://pypi.org/simple/',
            have_server_supported_tags=True
        ),
    ])
