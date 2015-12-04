#!/usr/bin/env python

import json
import os
import subprocess
import sys
import traceback

#chromium_src_path = os.environ['CHROMIUM_SRC_PATH']
chromium_src_path = os.path.abspath(
    os.path.join(os.environ['HOME'], 'work', 'cr-primary', 'src'))

blink_bindings_path = os.path.join(
    chromium_src_path, 'third_party', 'WebKit', 'Source', 'bindings',
    'scripts')
sys.path.insert(0, blink_bindings_path)

from blink_idl_lexer import BlinkIDLLexer
from blink_idl_parser import BlinkIDLParser
from blink_idl_parser import ListFromConcat
import collect_idls_into_json as co


# Specialized Lexer & Parser for WebKit r147502. Its syntax is similar to
# old spec, but has some extensions.

class WebKitIDLLexer(BlinkIDLLexer):
    def __init__(self, debug=False):
        old_keywors = {
            'char': 'CHAR',
            'in': 'IN',
            'int' : 'INT',
            'raises': 'RAISES',
            'signed': 'SIGNED',
        }
        self._AddKeywords(old_keywors)
        super(WebKitIDLLexer, self).__init__(debug=debug)


class WebKitIDLParser(BlinkIDLParser):
    def __init__(self, debug=False):
        lexer = WebKitIDLLexer(debug=debug)
        super(WebKitIDLParser, self).__init__(lexer=lexer, debug=debug)

    def p_Definitions(self, p):
        """Definitions : ExtendedAttributeList Definition Definitions
                       | """
        if len(p) > 1:
            p[2].AddChildren(p[1])
            p[0] = ListFromConcat(p[2], p[3])

    def p_Argument(self, p):
        """Argument : IN ExtendedAttributeList OptionalOrRequiredArgument
                    | ExtendedAttributeList OptionalOrRequiredArgument"""
        if len(p) > 3:
            p[3].AddChildren(p[2])
            p[0] = p[3]
        else:
            p[2].AddChildren(p[1])
            p[0] = p[2]

    def p_OperationRest(self, p):
        """OperationRest : OptionalIdentifier '(' ArgumentList ')' Raises ';'"""
        arguments = self.BuildProduction('Arguments', p, 2, p[3])
        p[0] = self.BuildNamed('Operation', p, 1, arguments)

    def p_Raises(self, p):
        """Raises : RAISES '(' ScopedNameList ')'
                  |"""
        pass

    def p_ScopedNameList(self, p):
        """ScopedNameList : identifier ScopedNames
                          |"""
        pass

    def p_ScopedNames(self, p):
        """ScopedNames : ',' identifier ScopedNames
                       |"""
        pass

    def p_AttributeRest(self, p):
        """AttributeRest : ATTRIBUTE ExtAttrNoEmpty Type AttributeName LegacySuffix ';'
                         | ATTRIBUTE Type AttributeName LegacySuffix ';'"""
        if len(p) > 6:
            p[0] = self.BuildNamed('Attribute', p, 4, p[3])
        else:
            p[0] = self.BuildNamed('Attribute', p, 3, p[2])

    def p_AttributeNameKeyword(self, p):
        """AttributeNameKeyword : REQUIRED
                                | OBJECT"""
        p[0] = p[1]

    def p_LegacySuffix(self, p):
        """LegacySuffix : GETTER Raises
                        | SETTER Raises
                        | SETTER Raises ',' GETTER Raises
                        | GETTER Raises ',' SETTER Raises
                        |"""
        pass

    def p_ExtendedAttributeIdentNumber(self, p):
        """ExtendedAttributeIdentNumber : identifier '=' integer"""
        value = self.BuildAttribute('VALUE', p[3])
        p[0] = self.BuildNamed('ExtAttribute', p, 1, value)

    def p_ExtendedAttributeLegacyList(self, p):
        """ExtendedAttributeLegacyList : identifier '=' LegacyArgList"""
        p[0] = self.BuildNamed('ExtAttribute', p, 1, None)

    def p_ExtendedAttributeKeyword(self, p):
        """ExtendedAttributeKeyword : identifier '=' ExtAttrKeyword"""
        value = self.BuildAttribute('VALUE', p[3])
        p[0] = self.BuildNamed('ExtAttribute', p, 1, value)

    def p_ExtAttrKeyword(self, p):
        """ExtAttrKeyword : DOUBLE
                          | FLOAT
                          | UNSIGNED CHAR 
                          | SIGNED CHAR
                          | CHAR
                          | UnsignedIntegerType"""
        p[0] = p[1]

    def p_LegacyArgList(self, p):
        """LegacyArgList : identifier LegacyArgs
                   |"""
        pass

    def p_LegacyArgs(self, p):
        """LegacyArgs : '&' identifier LegacyArgs
                      | '|' identifier LegacyArgs
                      |"""
        pass

    def p_ExtendedAttribute(self, p):
        """ExtendedAttribute : ExtendedAttributeNoArgs
                             | ExtendedAttributeArgList
                             | ExtendedAttributeIdent
                             | ExtendedAttributeIdentNumber
                             | ExtendedAttributeIdentList
                             | ExtendedAttributeNamedArgList
                             | ExtendedAttributeLegacyList
                             | ExtendedAttributeKeyword
                             | ExtendedAttributeStringLiteral
                             | ExtendedAttributeStringLiteralList"""
        p[0] = p[1]

    def p_ExtAttrNoEmpty(self, p):
        """ExtAttrNoEmpty : '[' ExtendedAttribute ExtendedAttributes ']'"""
        items = ListFromConcat(p[2], p[3])
        p[0] = self.BuildProduction('ExtAttributes', p, 1, items)

    def p_Interface(self, p):
        """Interface : INTERFACE ExtAttrNoEmpty identifier Inheritance '{' InterfaceMembers '}' ';'
                     | INTERFACE identifier Inheritance '{' InterfaceMembers '}' ';'"""
        if len(p) > 8:
            p[0] = self.BuildNamed('Interface', p, 3, ListFromConcat(p[4], p[6]))
        else:
            p[0] = self.BuildNamed('Interface', p, 2, ListFromConcat(p[3], p[5]))

    def p_Inheritance(self, p):
        """Inheritance : ':' ScopedNameList
                       |"""
        if len(p) > 1:
            p[0] = self.BuildNamed('Inherit', p, 2)

    def p_IntegerType(self, p):
        """IntegerType : SHORT
                       | INT
                       | LONG OptionalLong"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = p[1] + p[2]


_BLACKLISTED_IDL_FILES = [
    'InjectedScriptHost.idl',
    'InspectorInstrumentation.idl',
]

def all_idl_files(path):
    for root, _, files in os.walk(path):
        for name in files:
            path = os.path.join(root, name)
            if not name.endswith('.idl'):
                continue
            if 'test' in path:
                continue
            if name in _BLACKLISTED_IDL_FILES:
                continue
            yield path


def parse_file(parser, path):
    preprocessed = subprocess.check_output([
        'gcc', '-E', '-P', '-x', 'c++', path])
    out = parser.ParseText(path, preprocessed)
    out.SetProperty('ERRORS', parser.GetErrors())
    return out


def definitions_under_path(parser, path):
    path = os.path.abspath(path)
    for filename in all_idl_files(path):
        definitions = parse_file(parser, filename)
        if parser.GetErrors() > 0:
            raise Exception('Failed to parse %s' % filename)
        for definition in definitions.GetChildren():
            yield definition


def safe_convert(definition):
    try:
        return co.interface_node_to_dict(definition)
    except Exception as e:
        traceback.print_exc()
        print e
        import pdb
        pdb.set_trace()


def parse_single_file(path):
    parser = WebKitIDLParser(debug=True)
    try:
        defs = parse_file(parser, path)
    except:
        import pdb
        pdb.set_trace()

def parse_webkit_repository(path):
    parser = WebKitIDLParser(debug=False)
    # No partials and implements in old WebKit IDLs.
    interfaces = {definition.GetName(): safe_convert(definition)
                  for definition in definitions_under_path(parser, path)
                  if not co.is_partial(definition)}
    print(json.dumps(interfaces, sort_keys=True, indent=2))

def parse_blink_repository(path):
    parser = BlinkIDLParser()
    definitions = [d for d in definitions_under_path(parser, path)]
    interfaces = {definition.GetName(): safe_convert(definition)
                  for definition in definitions
                  if not co.is_partial(definition)}
    partials = {definition.GetName(): safe_convert(definition)
                for definition in definitions
                if co.is_partial(definition)}
    merged = co.merge_partial_dicts(interfaces, partials)
    implement_node_list = [definition
                           for definition in definitions
                           if co.is_implements(definition)]
    co.merge_implement_nodes(merged, implement_node_list)
    print(json.dumps(merged, sort_keys=True, indent=2))
    

def main(args):
    path = args[0]
    if path.endswith('.idl'):
        parse_single_file(path)
    elif 'WebCore' in path:
        parse_webkit_repository(path)
    else:
        parse_blink_repository(path)


if __name__ == '__main__':
    main(sys.argv[1:])
