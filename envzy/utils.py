from __future__ import annotations

import os
import sys
import traceback
import types
from contextlib import contextmanager
from collections import defaultdict
from functools import lru_cache
from inspect import isclass, getmro
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Any, Tuple, Dict, FrozenSet, Optional, Iterator

import importlib_metadata
from importlib_metadata import Distribution as BaseDistribution
from packaging.requirements import Requirement, InvalidRequirement


@contextmanager
def change_working_directory(path: str):
    old_cwd = os.getcwd()

    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextmanager
def tmp_cwd() -> Iterator[str]:
    with TemporaryDirectory() as tmp:
        with change_working_directory(tmp):
            yield tmp


def canonize_name(name: str) -> str:
    return name.replace('_', '-')


class Distribution:
    def __init__(self, base: BaseDistribution):
        self.base = base

    @property
    def name(self) -> str:
        return canonize_name(self.base.name)

    def __getattr__(self, name: str):
        return getattr(self.base, name)


def getmembers(object: Any, predicate=None) -> List[Tuple[str, Any]]:
    """Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate.

    NB: this function is a copypaste from inspect.py with small addition:
    we are catching TypeError in addition to AttributeError
    and ModuleNotFoundError in addition to other AttributeError at other try/except.
    """
    if isclass(object):
        mro = (object,) + getmro(object)
    else:
        mro = ()
    results: List[Tuple[str, Any]] = []
    processed = set()
    names = dir(object)
    # :dd any DynamicClassAttributes to the list of names if object is a class;
    # this may result in duplicate entries if, for example, a virtual
    # attribute with the same name as a DynamicClassAttribute exists
    try:
        for base in object.__bases__:
            for k, v in base.__dict__.items():
                if isinstance(v, types.DynamicClassAttribute):
                    names.append(k)
    except (AttributeError, TypeError):
        pass
    for key in names:
        # First try to get the value via getattr.  Some descriptors don't
        # like calling their __get__ (see bug #1785), so fall back to
        # looking in the __dict__.
        try:
            value = getattr(object, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except (AttributeError, ImportError):
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                # could be a (currently) missing slot member, or a buggy
                # __dir__; discard and move on
                continue
        except RuntimeError:
            continue
        if not predicate or predicate(value):
            results.append((key, value))
        processed.add(key)
    results.sort(key=lambda pair: pair[0])
    return results


def check_url_is_local_file(url: str) -> bool:
    file_scheme = 'file://'

    if not url.startswith(file_scheme):
        return False

    raw_path = url[len(file_scheme):]
    path = Path(raw_path)

    # idk if there may be relative paths in direct_url.json,
    # but if it is, next code will work badly with it.
    if not path.is_absolute():
        return False

    return path.exists()


@lru_cache(maxsize=None)
def get_stdlib_module_names() -> FrozenSet[str]:
    try:
        return frozenset(sys.stdlib_module_names)  # type: ignore
    except AttributeError:
        # python_version < 3.10
        from stdlib_list import stdlib_list

        return frozenset(stdlib_list())


@lru_cache(maxsize=None)
def get_builtin_module_names() -> FrozenSet[str]:
    return frozenset(sys.builtin_module_names)


@lru_cache(maxsize=None)
def get_names_to_distributions() -> Dict[str, Distribution]:
    result: Dict[str, Distribution] = {}
    # NB: importlib_metadata.Distribution calls may return different
    # results in depends from cwd.
    # So we are moving cwd into tmp dir in name of results repeatability.
    # In case of PermissionError, location of tmp dir can be moved with
    # TMPDIR env variable.
    with tmp_cwd():
        for base_distribution in importlib_metadata.distributions():
            distribution = Distribution(base_distribution)
            result[distribution.name] = distribution

    return result


@lru_cache(maxsize=None)  # cache size is about few MB
def get_files_to_distributions() -> Dict[str, Distribution]:
    result = {}

    for distribution in get_names_to_distributions().values():
        for path in get_distribution_files(distribution):
            fullpath = distribution.locate_file(path)
            result[str(fullpath)] = distribution

    return result


def is_path_package_meta(path: Path) -> bool:
    return any(
        part.endswith('.dist-info') or part.endswith('.egg-info')
        for part in path.parts
    )


def check_distribution_is_meta_package(distribution: Distribution) -> bool:
    distribution_files = get_distribution_files(distribution)
    if not distribution_files:
        # NB: .egg-info packages and some apt-packages doesn't have
        # a dist-info directory and importlib.metadata fails to generate
        # files list
        return False

    return all(
        is_path_package_meta(path)
        for path in distribution_files
    )


def get_name_from_requirement_string(requirement_string: str) -> Optional[str]:
    try:
        requirement = Requirement(requirement_string)
    except InvalidRequirement:
        return None

    return canonize_name(requirement.name)


@lru_cache(maxsize=None)  # cache size is about few MB
def get_requirements_to_meta_packages() -> Dict[str, List[Distribution]]:
    result: Dict[str, List[Distribution]] = defaultdict(list)

    with tmp_cwd():
        for distribution in get_names_to_distributions().values():
            if not check_distribution_is_meta_package(distribution):
                continue

            for requirement_string in distribution.requires or ():
                name = get_name_from_requirement_string(requirement_string)
                if name:
                    result[name].append(distribution)

    return dict(result)


def is_wellknown_fake_module(top_level_module_name: str, module_filename: str) -> bool:
    if top_level_module_name == 'torch':
        module_file_basename = os.path.basename(module_filename)
        if module_file_basename in ['torch.ops', '_ops.py', '_classes.py']:
            return True
    return False


def is_lazy_module(module: types.ModuleType) -> bool:
    module_package = getattr(module.__class__, '__module__', None)
    module_name = type(module).__name__
    return (
        (module_package == 'tensorboard.lazy' and module_name == 'LazyModule')
        or
        (module_package == 'tensorflow.python.util.lazy_loader' and module_name == 'KerasLazyLoader')
    )


def get_distribution_files(distribution: Distribution) -> Tuple[Path, ...]:
    try:
        # NB: TODO: distribution.files could be empty in case of
        # dist-packages & .egg-info.
        # Primarily it affects python packages, installed
        # via apt-get, for example.
        # So if user working in non-isolated environment
        # and using packages from dist-packages, we will
        # mistreat these packages as local in future while
        # classification.
        files = distribution.files
        if files:
            return tuple(
                distribution.locate_file(path).resolve()
                for path in files
            )
    except ValueError:
        _, _, raw_tb = sys.exc_info()
        # NB: I dont wanna to supress any random errors,
        # only well-known ones
        if not is_exception_in_file(raw_tb, 'pathlib.py'):
            raise

        # so well-known thing in that case, that if distribution
        # have .egg-info instead .dist-info AND it have files outside
        # site-packages, distribution.files fails

    # this is the case for some .egg-info packages
    # NB: it is copy-paste from importlib_metadata but without
    # calculation of relative paths from package root, because it breaks
    text = distribution.read_text('installed-files.txt')
    subdir = getattr(distribution, '_path', None)
    if not text or not subdir:
        return ()

    paths = tuple(
        (subdir / name)
        .resolve()
        for name in text.splitlines()
    )

    return paths


def is_exception_in_file(raw_tb: Optional[types.TracebackType], filename: str) -> bool:
    if not raw_tb:
        return False

    tb = traceback.extract_tb(raw_tb)
    last_frame = tb[-1]
    last_frame_path = Path(last_frame.filename)
    return last_frame_path.parts[-1] == filename
