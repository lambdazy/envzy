from __future__ import annotations

import sys
import json
import pathlib

from typing import List, Tuple

import pytest


@pytest.fixture(scope="module")
def vcr_cassette_dir(request, get_test_data_path) -> str:
    module = request.node.fspath  # current test file

    # /home/<user>/.../lzy/pylzy/tests/utils/test_gprc.py
    module_filename = pathlib.Path(module)

    # /home/<user>/.../lzy/pylzy/tests/
    conftest_dir = pathlib.Path(__file__).parent

    # utils/test_grpc.py
    rel_module_path = module_filename.relative_to(conftest_dir)

    # utils/test_grpc
    cassete_dir = rel_module_path.with_suffix('')

    # /home/<user>/.../lzy/pylzy/tests/test_data/cassetes/utils/test_grpc/
    return str(get_test_data_path("cassettes", cassete_dir))


@pytest.fixture(scope="session")
def vcr_config():
    return {"decode_compressed_response": True}


@pytest.fixture(scope='session')
def get_test_data_path():
    base = pathlib.Path(__file__).parent / 'test_data'

    def getter(*relative):
        return base.joinpath(*relative)

    return getter


@pytest.fixture(scope='function')
def with_test_modules(get_test_data_path, monkeypatch):
    with monkeypatch.context() as m:
        m.syspath_prepend(get_test_data_path())
        yield


@pytest.fixture(scope='session')
def pypi_index_url():
    from envzy.pypi import PYPI_INDEX_URL_DEFAULT

    return PYPI_INDEX_URL_DEFAULT


@pytest.fixture(scope='session')
def pypi_index_url_testing():
    return 'https://test.pypi.org/simple'


@pytest.fixture(scope='session')
def env_prefix() -> pathlib.Path:
    return pathlib.Path(sys.exec_prefix).resolve()


@pytest.fixture(scope='session')
def site_packages(env_prefix: pathlib.Path) -> pathlib.Path:
    path = env_prefix / "lib" / "python{}.{}".format(*sys.version_info) / "site-packages"
    return path.resolve()


@pytest.fixture
def allowed_hosts() -> List[str]:
    return ['localhost', '127.0.0.1', '::1']
