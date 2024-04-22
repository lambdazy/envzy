from __future__ import annotations

import sys
import pytest
from envzy import AutoExplorer, EnvironmentSpec
from envzy.packages import PypiDistribution, LocalDistribution


def test_defaults(pypi_index_url):
    # NB: I'm not sure if it have any sense to do such test...
    # but at least I checking possibility to instantiate
    # explorer without any arguments
    explorer = AutoExplorer()

    assert explorer.additional_pypi_packages == {}
    assert explorer.pypi_index_url == pypi_index_url
    assert explorer.target_python == sys.version_info[:2]
    assert explorer.search_stop_list == ()


@pytest.mark.vcr
def test_get_environment_spec(pypi_index_url, site_packages, env_prefix):
    import lzy_test_project

    exporer = AutoExplorer()

    spec = exporer.get_environment_spec({'foo': lzy_test_project})

    assert spec == EnvironmentSpec(
        packages=[
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
            PypiDistribution(
                name='sampleproject',
                version='3.0.0',
                pypi_index_url='https://pypi.org/simple/',
                have_server_supported_tags=True
            ),
        ],
        local_module_paths=[
            f'{site_packages}/lzy_test_project',
            f'{site_packages}/lzy_test_project-3.0.0.dist-info'
        ],
        pypi_packages={
            'sampleproject': '3.0.0'
        },
        console_scripts=[
            f'{env_prefix}/bin/lzy_test_project_bin'
        ]
    )
