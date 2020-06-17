# -*- coding: utf-8 -*-

"""
Include YAML files within YAML
"""

import io
import os.path
import re
from glob import iglob
from sys import version_info

import yaml

try:
    from yaml import FullLoader
except ImportError:
    FullLoader = None

__all__ = ['YamlIncludeConstructor']

PYTHON_MAYOR_MINOR = '{0[0]}.{0[1]}'.format(version_info)

WILDCARDS_REGEX = re.compile(r'^.*(\*|\?|\[!?.+\]).*$')


class YamlIncludeConstructor:
    """The `include constructor` for PyYAML Loaders

    Call :meth:`add_to_loader_class` or :meth:`yaml.Loader.add_constructor` to add it into loader.

    In YAML files, use ``!include`` to load other YAML files as below::

        !include [dir/**/*.yml, true]

    or::

        !include {pathname: dir/abc.yml, encoding: utf-8}

    """

    DEFAULT_ENCODING = 'utf-8'
    DEFAULT_TAG_NAME = '!include'

    def __init__(self, base_dir=None, encoding=None):
        # type:(str, str)->YamlIncludeConstructor
        """
        :param str base_dir: Base directory where search including YAML files

            :default: ``None``:  include YAML files from current working directory.

        :param str encoding: Encoding of the YAML files

            :default: ``None``:  Not specified
        """
        self._base_dir = base_dir
        self._encoding = encoding

    def __call__(self, loader, node):
        args = []
        kwargs = {}
        if isinstance(node, yaml.nodes.ScalarNode):
            args = [loader.construct_scalar(node)]
        elif isinstance(node, yaml.nodes.SequenceNode):
            args = loader.construct_sequence(node)
        elif isinstance(node, yaml.nodes.MappingNode):
            kwargs = loader.construct_mapping(node)
        else:
            raise TypeError('Un-supported YAML node {!r}'.format(node))
        return self.load(loader, *args, **kwargs)

    @property
    def base_dir(self):  # type: ()->str
        """Base directory where search including YAML files

        :rtype: str
        """
        return self._base_dir

    @base_dir.setter
    def base_dir(self, value):  # type: (str)->None
        self._base_dir = value

    @property
    def encoding(self):  # type: ()->str
        """Encoding of the YAML files

        :rtype: str
        """
        return self._encoding

    @encoding.setter
    def encoding(self, value):  # type: (str)->None
        self._encoding = value

    def load(self, loader, pathname, recursive=False, encoding=None):
        """Once add the constructor to PyYAML loader class,
        Loader will use this function to include other YAML fils
        on parsing ``"!include"`` tag

        :param loader: Instance of PyYAML's loader class
        :param str pathname: pathname can be either absolute (like /usr/src/Python-1.5/Makefile) or relative (like ../../Tools/*/*.gif), and can contain shell-style wildcards

        :param bool recursive: If recursive is true, the pattern ``"**"`` will match any files and zero or more directories and subdirectories. If the pattern is followed by an os.sep, only directories and subdirectories match.

            Note:
             Using the ``"**"`` pattern in large directory trees may consume an inordinate amount of time.

        :param str encoding: YAML file encoding

            :default: ``None``: Attribute :attr:`encoding` or constant :attr:`DEFAULT_ENCODING` will be used to open it

        :return: included YAML file, in Python data type

        .. warning:: It's called by :mod:`yaml`. Do NOT call it yourself.
        """
        
        os_env_path_matcher = re.compile(r'\$\{([^}^{]+)\}')
        import sys
        try:
            # First check if the value is defined in the SHELL environment
            varsFromYamlConfigRaw = os.environ["config"]
            varsFromYamlConfig = yaml.load(varsFromYamlConfigRaw,Loader=FullLoader)
            #print(varsFromYamlConfig,file=sys.stderr)
            stringToBeSubstituted = pathname
            valueNames = os_env_path_matcher.findall(stringToBeSubstituted)
            for valueName in valueNames:
                try:
                    # First check if the value is defined in the SHELL environment
                    aValue = os.environ[valueName]
                except KeyError:
                    # If that fails check if it's defined in yaml
                    # Split the value name in case it refers to a nested value
                    keyList=valueName.split(".")
                    try:
                        # Start with the root of the dictionary containing all variables
                        aValue = varsFromYamlConfig
                        # In case of nested dictionary iterate every dictionary level
                        for akey in keyList:
                            #print(akey+"sa",file=sys.stderr)
                            aValue = aValue[akey]
                    except KeyError:
                        print("No value for variable: {}".format(valueName),file=sys.stderr)
                        aValue=""
                stringToBeSubstituted = re.sub('\${'+valueName+'}',str(aValue),str(stringToBeSubstituted))
            pathname = stringToBeSubstituted
        except KeyError:
            pass #print("No config!",file=sys.stderr)
        
        if not encoding:
            encoding = self._encoding or self.DEFAULT_ENCODING
        if self._base_dir:
            pathname = os.path.join(self._base_dir, pathname)
        if re.match(WILDCARDS_REGEX, pathname):
            result = []
            if PYTHON_MAYOR_MINOR >= '3.5':
                iterator = iglob(pathname, recursive=recursive)
            else:
                iterator = iglob(pathname)
            for path in iterator:
                if os.path.isfile(path):
                    with io.open(path, encoding=encoding) as fp:  # pylint:disable=invalid-name
                        result.append(YamlIncludeConstructor.loadYaml(path,fp,loader))
            return result
        with io.open(pathname, encoding=encoding) as fp:  # pylint:disable=invalid-name
            return YamlIncludeConstructor.loadYaml(pathname,fp,loader)

    @classmethod
    def loadYaml(cls, path, file, loader):
        if path.lower().endswith(('.yaml', '.yml')):
            return yaml.load(file, type(loader))
        else:
            return file.read()

    @classmethod
    def add_to_loader_class(cls, loader_class=None, tag=None, **kwargs):
        # type: (type(yaml.Loader), str, **str)-> YamlIncludeConstructor
        """
        Create an instance of the constructor, and add it to the YAML `Loader` class

        :param loader_class: The `Loader` class add constructor to.

            .. attention:: This parameter **SHOULD** be a **class type**, **NOT** object.

            It's one of following:

                - :class:`yaml.BaseLoader`
                - :class:`yaml.UnSafeLoader`
                - :class:`yaml.SafeLoader`
                - :class:`yaml.Loader`
                - :class:`yaml.FullLoader`
                - :class:`yaml.CBaseLoader`
                - :class:`yaml.CUnSafeLoader`
                - :class:`yaml.CSafeLoader`
                - :class:`yaml.CLoader`
                - :class:`yaml.CFullLoader`

            :default: ``None``:

                - When :mod:`pyyaml` 3.*: Add to PyYAML's default `Loader`
                - When :mod:`pyyaml` 5.*: Add to `FullLoader`

        :type loader_class: type

        :param str tag: Tag's name of the include constructor.

          :default: ``""``: Use :attr:`DEFAULT_TAG_NAME` as tag name.

        :param kwargs: Arguments passed to construct function

        :return: New created object
        :rtype: YamlIncludeConstructor
        """
        if tag is None:
            tag = ''
        tag = tag.strip()
        if not tag:
            tag = cls.DEFAULT_TAG_NAME
        if not tag.startswith('!'):
            raise ValueError('`tag` argument should start with character "!"')
        instance = cls(**kwargs)
        if loader_class is None:
            yaml.add_constructor(tag, instance)
        else:
            yaml.add_constructor(tag, instance, loader_class)
        return instance
