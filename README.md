A library that explores dependencies from a given module or namespace in a local Python environment, then classifies these dependencies.

The library was isolated from the [LZY project](https://github.com/lambdazy/lzy)'s codebase to ensure reusability and reduce the difficulty of dependency management.

If you are interested in using our library, please contact us via Github Issues.

## Brief example

```python
In [1]: from envzy import AutoExplorer

In [2]: explorer = AutoExplorer(pypi_index_url='https://pypi.org/simple', additional_pypi_packages={}, target_python=(3, 9))

In [3]: explorer.get_local_module_paths({'foo': AutoExplorer})
Out[3]: ['/home/lipkin/repos/envzy/envzy']

In [4]: explorer.get_pypi_packages({'foo': AutoExplorer})
Out[4]:
{'mailbits': '0.2.1',
 'urllib3': '2.0.7',
 'charset-normalizer': '3.3.1',
 'certifi': '2023.7.22',
 'pydantic_core': '2.10.1',
 'packaging': '23.2',
 'soupsieve': '2.5',
 'importlib-metadata': '6.8.0',
 'pypi-simple': '1.2.0',
 'annotated-types': '0.6.0',
 'idna': '3.4',
 'zipp': '3.17.0',
 'attrs': '23.1.0',
 'beautifulsoup4': '4.12.2',
 'pydantic': '2.4.2',
 'typing_extensions': '4.8.0',
 'requests': '2.31.0'}
```
