#!/usr/bin/env python

"""Parse IDL files and dump them as json.

TODOs:
- Support "Supplemental" in WebKit

"""

from collections import defaultdict
import json
import os
import subprocess
import sys

import insert_crpath

from blink_idl_parser import BlinkIDLParser
from idl_definitions import IdlDefinitions, Visitor

from old_webkit_idl_parser import WebKitIDLParser


class ConverterBase(object):
    """Parse IDL files, convert into a JSON object, merging implements/partial.
    """

    def __init__(self, parser):
        self._parser = parser
        self._partial_interfaces = {}
        self._implements = defaultdict(list)
        self._interfaces = {}

    def _read_idl_content(self, path):
        with open(path) as f:
            return f.read()

    def _rewrite_definitions(self, definitions):
        return definitions

    def _post_process(self, interfaces):
        return interfaces

    def process_idl_file(self, path):
        content = self._read_idl_content(path)
        idl_nodes = self._parser.ParseText(path, content)
        if self._parser.GetErrors() > 0:
            raise Exception('Failed to parse %s' % path)
        idl_name, _ = os.path.splitext(os.path.basename(path))
        definitions = IdlDefinitions(idl_name, idl_nodes)
        definitions = self._rewrite_definitions(definitions)

        self._interfaces.update({
            interface.name: interface
            for interface in definitions.interfaces.itervalues()
            if not interface.is_partial})
        self._partial_interfaces.update({
            interface.name: interface
            for interface in definitions.interfaces.itervalues()
            if interface.is_partial})
        for impl in definitions.implements:
            self._implements[impl.left_interface].append(impl.right_interface)

    def _merge_interface(self, dest, src):
        # TODO(bashi): Maybe merge setlike and maplike
        dest.attributes.extend(src.attributes)
        dest.constants.extend(src.constants)
        dest.operations.extend(src.operations)
        
    def _merge_implements(self, interface):
        for impl_name in self._implements[interface.name]:
            impl_interface = self._interfaces.get(impl_name)
            if not impl_interface:
                sys.stderr.write(
                    'Warning: %s implements %s, but cannot find %s\n' % (
                    interface.name, impl_name, impl_name))
                continue
            self._merge_interface(interface, impl_interface)

    def _merge_partial(self, partial_interface):
        interface = self._interfaces.get(partial_interface.name)
        if not interface:
            sys.stderr.write(
                'Warning: Partial interface %s is found but no original '
                'definition found. Ignore it.\n' % partial_interface.name)
            return
        self._merge_interface(interface, partial_interface)

    def _merge(self):
        for partial_interface in self._partial_interfaces.itervalues():
            self._merge_partial(partial_interface)
        for interface in self._interfaces.itervalues():
            self._merge_implements(interface)
        return self._interfaces

    def to_json(self):
        interfaces = self._merge()
        interfaces = self._post_process(interfaces)
        def _default(obj):
            return obj.__dict__
        return json.dumps(interfaces, indent=2,
                          default=_default, sort_keys=True)


class BlinkConverter(ConverterBase):
    def __init__(self):
        super(BlinkConverter, self).__init__(BlinkIDLParser())


class NameRewriteVisitor(Visitor):
    def __init__(self, name_map):
        self._name_map = name_map

    def rewrite(self, interface):
        interface.accept(self)

    def visit_typed_object(self, typed_object):
        if not typed_object.idl_type:
            return
        original = typed_object.idl_type.base_type
        typed_object.idl_type.base_type = self._name_map.get(original, original)


class WebKitConverter(ConverterBase):
    def __init__(self):
        super(WebKitConverter, self).__init__(WebKitIDLParser())
        self._interface_name_map = {}

    def _read_idl_content(self, path):
        # WebKit IDLs could have some macros. Remove them.
        preprocessed = subprocess.check_output([
            'gcc', '-E', '-P', '-x', 'c++', path])
        return preprocessed

    def _rewrite_definitions(self, definitions):
        for interface in definitions.interfaces.itervalues():
            self._rewrite_interface(interface)
        return definitions

    def _rewrite_interface(self, interface):
        interface_name = interface.extended_attributes.get('InterfaceName')
        if interface_name:
            self._interface_name_map[interface.name] = interface_name
            interface.name = interface_name

    def _post_process(self, interfaces):
        name_rewriter = NameRewriteVisitor(self._interface_name_map)
        for interface in interfaces.itervalues():
            name_rewriter.rewrite(interface)
        return interfaces


_BLACKLISTED_IDL_FILES = [
    'InjectedScriptHost.idl',
    'InspectorInstrumentation.idl',
]


def all_idl_files(basedir):
    for root, _, files in os.walk(basedir):
        for name in files:
            path = os.path.join(root, name)
            if not name.endswith('.idl'):
                continue
            if 'test' in path:
                continue
            if name in _BLACKLISTED_IDL_FILES:
                continue
            yield path


def target_files(path):
    if path.endswith('.idl'):
        return [path]
    return all_idl_files(path)


def _create_converter(path):
    # Assumes that if the absolute path contains 'WebCore', it's WebKit.
    if 'WebCore' in os.path.abspath(path):
        return WebKitConverter()
    return BlinkConverter()


def to_json(path):
    converter = _create_converter(path)
    for filename in target_files(path):
        converter.process_idl_file(filename)
    return converter.to_json()


def main(args):
    print to_json(args[0])


if __name__ == '__main__':
    main(sys.argv[1:])
