from __future__ import annotations

import sys
from envzy import AutoExplorer


def test_defaults(pypi_index_url):
    # NB: I'm not sure if it have any sense to do such test...
    # but at least I checking possibility to instantiate
    # explorer without any arguments
    explorer = AutoExplorer()

    assert explorer.additional_pypi_packages == {}
    assert explorer.pypi_index_url == pypi_index_url
    assert explorer.target_python == sys.version_info[:2]
    assert explorer.search_stop_list == ()
