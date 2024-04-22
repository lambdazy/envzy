from __future__ import annotations

from abc import abstractmethod

from .search import VarsNamespace
from .spec import ModulePathsList, PackagesDict, EnvironmentSpec


class BaseExplorer:
    @abstractmethod
    def get_local_module_paths(self, namespace: VarsNamespace) -> ModulePathsList:
        raise NotImplementedError

    @abstractmethod
    def get_pypi_packages(self, namespace: VarsNamespace) -> PackagesDict:
        raise NotImplementedError

    @abstractmethod
    def get_environment_spec(self, namespace: VarsNamespace) -> EnvironmentSpec:
        raise NotImplementedError
