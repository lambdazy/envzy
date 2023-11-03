from __future__ import annotations

import sys
from dataclasses import dataclass, field
from logging import getLogger
from typing import List, Type, TypeVar, Tuple, Union, Iterable

from .base import BaseExplorer, ModulePathsList, PackagesDict
from .classify import ModuleClassifier
from .search import VarsNamespace, get_transitive_namespace_dependencies
from .packages import (
    BrokenModules,
    LocalPackage,
    BasePackage,
    PypiDistribution,
    LocalDistribution
)
from .pypi import PYPI_INDEX_URL_DEFAULT

logger = getLogger(__name__)

P = TypeVar('P', bound=BasePackage)

PythonVersion = Union[Tuple[int, int], Tuple[int, int, int]]


@dataclass
class AutoExplorer(BaseExplorer):
    pypi_index_url: str = PYPI_INDEX_URL_DEFAULT
    additional_pypi_packages: PackagesDict = field(default_factory=dict)
    target_python: PythonVersion = sys.version_info[:2]
    search_stop_list: Iterable = ()

    def get_local_module_paths(self, namespace: VarsNamespace) -> ModulePathsList:
        packages = self._get_packages(namespace, LocalPackage)

        filtered: List[LocalPackage] = []
        binary: List[LocalPackage] = []
        nonbinary: List[LocalPackage] = []

        for package in packages:
            if package.name in self.additional_pypi_packages:
                array = filtered
            elif package.is_binary:
                array = binary
            else:
                array = nonbinary

            array.append(package)

        packages_with_bad_paths = [
            p for p in nonbinary
            if isinstance(p, LocalDistribution) and p.bad_paths
        ]

        if filtered:
            logger.debug(
                "Some dependency packages were classified as local but filtered due "
                "to explicit value of additional_pypi_packages: %s",
                filtered
            )

        if binary:
            logger.warning(
                "Some dependency packages were classified as local but they "
                "contain a binary files; these packages wouldn't be transferred to a remote "
                "host. If you need these packages, specify it explicitly "
                "at additional_pypi_packages to force-classify it as pypi packages: %s",
                binary,
            )

        if packages_with_bad_paths:
            logger.warning(
                "Some dependency packages were classified as local but they "
                "contain files with non-standard paths; these paths wouldn't be transferred to "
                "a remote host, but packages will be transferred without it. "
                "In case of any troubles with these packages, specify it explicitly "
                "at additional_pypi_packages to force-classify it as pypi packages: %s",
                packages_with_bad_paths
            )

        if nonbinary:
            logger.debug(
                "Next dependency packages were classified as local packages "
                "and will be transfered to a remote host: %s",
                nonbinary
            )

        return list(set().union(*(p.paths for p in nonbinary)))

    def get_pypi_packages(self, namespace: VarsNamespace) -> PackagesDict:
        packages = self._get_packages(namespace, PypiDistribution)

        overrided: List[PypiDistribution] = []
        bad_platform: List[PypiDistribution] = []
        good: List[PypiDistribution] = []

        for package in packages:
            if package.name in self.additional_pypi_packages:
                array = overrided
            elif not package.have_server_supported_tags:
                array = bad_platform
            else:
                array = good

            array.append(package)

        if overrided:
            logger.debug(
                "Next dependency packages were classified as pypi packages "
                "but were overrided by additional_pypi_packages option: %s",
                overrided
            )

        if bad_platform:
            logger.warning(
                "Next dependency packages were classified as pypi packages "
                "but doesn't exist for Lzy server platform linux_x86_64 and requested "
                "python version %s "
                "and will be skipped: %s; if you will experience problems caused "
                "by absense of this packages on server, you should use manual python "
                "environment",
                self.target_python, bad_platform
            )

        return {
            **{p.name: p.version for p in good},
            **self.additional_pypi_packages
        }

    def _get_packages(
        self,
        namespace: VarsNamespace,
        filter_class: Type[P],
    ) -> List[P]:
        stop_list = frozenset(self.search_stop_list)
        modules = get_transitive_namespace_dependencies(namespace, stop_list=stop_list)

        classifier = ModuleClassifier(
            self.pypi_index_url,
            target_python=self.target_python
        )

        packages = classifier.classify(modules)
        broken = [p for p in packages if isinstance(p, BrokenModules)]
        if broken:
            logger.warning(
                'while exploring local environment we failed to classify some modules '
                'so these moduels will be omitted: %s', broken
            )

        return [p for p in packages if isinstance(p, filter_class)]
