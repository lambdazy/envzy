from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
from typing_extensions import TypeAlias

from .packages import BasePackage

ModulePathsList: TypeAlias = List[str]
PackagesDict: TypeAlias = Dict[str, str]
PackagesList: TypeAlias = List[BasePackage]


@dataclass
class EnvironmentSpec:
    packages: PackagesList
    local_module_paths: ModulePathsList
    pypi_packages: PackagesDict
    console_scripts: ModulePathsList
