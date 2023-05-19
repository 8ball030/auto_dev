
from __future__ import annotations

from auto_dev.polygon_api import PolygonAPI, keys_to_snake_case
from typing import Dict

import warnings
from solidity_parser import parser
import yaml
from pathlib import Path
from dataclasses import dataclass, field, fields
from enum import Enum
import json

from auto_dev.solidity_types import type_mapping

path = Path("auto_dev/data/contracts.yaml").absolute()
assert path.exists()

data = yaml.safe_load(path.read_text())
api = PolygonAPI()

# get raw
responses = []
for address in map(hex, data.get("addresses", [])):
    try:
        response = api.contract.get_source_code(address)
        responses.append(response)
    except Exception as error:
        print(f"FAILED: {address} - {error}")


def clean_code(s: str):
    return s[s.startswith("{{"):-s.endswith("}}")]


class EnumStrAndReprMixin:
    """Display Enum.value without classname prefix."""

    def __str__(self):
        return self.name

    __repr__ = __str__


@dataclass
class SkipDefaultFieldsReprMixin:
    """Display only non-empty & non-default value fields of a dataclass."""

    def __repr__(self) -> str:
        def condition(field: Field[Any]) -> TypeGuard[bool]:
            return field.repr and getattr(self, field.name) not in (field.default, "")

        def display(field: Any) -> str:
            return f"{field.name}={getattr(self, field.name)}"

        node_repr = ", ".join(map(display, filter(condition, fields(self))))
        return f"{self.__class__.__name__}({node_repr})"


@dataclass
class ParsingResults:
    success: dict = field(repr=False)  # TODO: only shows keys
    empty: dict = field(repr=False)
    failed: dict = field(repr=False)


@dataclass(repr=False)
class SourceCodeResult(SkipDefaultFieldsReprMixin):  # noqa
    """Representation of the idividual contract's data."""

    source_code: str = field(repr=False)
    abi: str = field(repr=False, default=None)
    contract_name: Optional[str] = None
    compiler_version: Optional[str] = field(repr=False, default=None)
    optimization_used: Optional[bool] = field(repr=False, default=None)
    runs: Optional[int] = field(repr=False, default=None)
    constructor_arguments: Optional[str] = field(repr=False, default=None)
    evm_version: Optional[str] = field(repr=False, default=None)
    library: Optional[str] = field(repr=False, default=None)
    license_type: Optional[str] = field(repr=False, default=None)
    proxy: Optional[bool] = None
    implementation: Optional[str] = field(repr=False, default=None)
    swarm_source: Optional[str] = field(repr=False, default=None)
    source_code_hash: Optional[str] = field(repr=False, default=None)
    source_code_meta_data: Optional[str] = field(repr=False, default=None)
    ast: Optional[str] = field(repr=False, default=None)
    source_list: Optional[List[str]] = field(repr=False, default=None)
    developer_doc: Optional[str] = field(repr=False, default=None)
    user_doc: Optional[str] = field(repr=False, default=None)


@dataclass
class SourceCode(SkipDefaultFieldsReprMixin):
    """Representation of the Solidity source code object."""

    language: str
    version: Optional[str] = field(repr=False, default=None)
    settings: Optional[Dict] = field(repr=False, default=None)
    sources: Optional[Dict[str, Dict[str, str]]
                      ] = field(repr=False, default=None)


def parse_source_code(responses):

    success, empty, failed = {}, {}, {}
    for response in responses:
        for response in responses:
            assert len(resp.result) == 1
            result = SourceCodeResult(**keys_to_snake_case(resp.result[0]))
            if not result.source_code:
                print(f"EMPTY: {address} - No SourceCode")
                empty[address] = result
                continue

            source_code = SourceCode(
                **json.loads(clean_code(result.source_code)))
            for path, v in source_code.sources.items():
                assert list(v.keys()) == ["content"]
                try:
                    node = parser.parse(v["content"])
                    success.setdefault(address, []).append(node)
                except Exception as error:
                    print(f"FAILED: {address} - {error}")
                    failed.setdefault(address, []).append(result)

    n_successes = sum(len(v) for v in success.values())
    n_failed = sum(len(v) for v in failed.values())
    print(f"Success: {n_successes}, Empty: {len(empty)}, Failed: {n_failed}")
    return ParsingResults(success, empty, failed)


parsing_result = parse_source_code(responses)


class Kind(EnumStrAndReprMixin, Enum):
    CONTRACT = "contract"
    ABSTRACT = "abstract"
    INTERFACE = "interface"
    LIBRARY = "library"


class NodeType(EnumStrAndReprMixin, Enum):
    ENUM_DEFINITION = "enum_defintion"
    EVENT_DEFINITION = "event_definition"
    FUNCTION_DEFINITION = "function_definition"
    MODIFIER_DEFINITION = "modifier_definition"
    STATE_VARIABLE_DECLARATION = "state_variable_declaration"
    STRUCT_DEFINITION = "struct_definition"
    USING_FOR_DECLARATION = "function_declaration"


class Visibility(EnumStrAndReprMixin, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"
    EXTERNAL = "external"
    DEFAULT = "default"  # same as internal


class StateMutability(EnumStrAndReprMixin, Enum):
    """State mutability of solidity function calls."""

    PURE = "pure"
    VIEW = "view"
    NONPAYABLE = "nonpayable"
    PAYABLE = "payable"


class ValueType(EnumStrAndReprMixin, Enum):
    BOOLEAN_LITERAL = "boolean_literal"  # value
    NUMBER_LITERAL = "number_literal"  # number, subdenomination
    # operator, left(ValueType), right(ValueType)
    BINARY_OPERATION = "binary_operation"
    IDENTIFIER = "identified"


@dataclass(repr=False)
class Variable(SkipDefaultFieldsReprMixin):
    name: str
    type: str
    visibility: Visibility = field(repr=False)
    is_state_var: bool = field(repr=False)
    is_declared_const: bool = field(repr=False)
    is_indexed: bool = field(repr=False)
    expression: Optional[dict] = field(repr=False, default=None)
    initial_value: Optional[dict] = field(repr=False, default=None)


@dataclass(repr=False)
class Event(SkipDefaultFieldsReprMixin):
    name: str
    parameters: List[Parameter] = field(repr=False)
    is_anonymous: bool


@dataclass(repr=False)
class Parameter(SkipDefaultFieldsReprMixin):
    name: str
    type: str
    is_state_var: bool = field(repr=False)
    is_indexed: bool = field(repr=False)
    storage_location: Optional[bool] = field(repr=False, default=None)


@dataclass(repr=False)
class ReturnParameter(SkipDefaultFieldsReprMixin):
    type: str
    is_state_var: bool = field(repr=False)
    is_indexed: bool = field(repr=False)
    name: Optional[str] = None
    storage_location: Optional[bool] = field(repr=False, default=None)


@dataclass
class Modifier:
    name: str
    parameters: list
    body: dict


@dataclass(repr=False)
class Function(SkipDefaultFieldsReprMixin):
    name: str
    parameters: list = field(repr=False)
    return_parameters: Union[dict, list] = field(repr=False)
    body: Union[dict, list] = field(repr=False)
    visibility: Visibility = field(repr=False)
    modifiers: list = field(repr=False)
    is_constructor: bool = field(repr=False)
    is_fallback: bool = field(repr=False)
    is_receive: bool = field(repr=False)
    state_mutability: StateMutability = field(repr=False)


@dataclass
class Declaration:
    type: str
    library: str


@dataclass(repr=False)
class StructMember(SkipDefaultFieldsReprMixin):
    type: str
    name: str
    storage_location: Optional[str] = None


@dataclass
class Struct:
    name: str
    members: list[StructMember] = field(repr=False)


def parse_enum_definition(node: parser.Node) -> Enum:
    """Parse Enum definition and generate Enum dynamically."""
    # TODO: registry such that we don't recreate each time
    return Enum(
        node.name,
        {k.name: k.name.lower() for k in node.members},
        type=EnumStrAndReprMixin,
        module=__name__,
    )


def parse_event_definition(node: parser.Node) -> Event:
    """Parse event definition.

    Events are unique and locally defined in a contract, hence no need for a registry.
    """

    return Event(
        name=node.name,
        parameters=parse_parameters(node),
        is_anonymous=node.isAnonymous,
    )


def parse_function_definition(node: parser.Node) -> Function:
    # [{'type': 'ModifierInvocation', 'name': 'nonReentrant', 'arguments': []}]
    # modifiers =
    state_mutability = node.stateMutability
    if state_mutability:
        state_mutability = StateMutability[node.stateMutability.upper()]
    return Function(
        name=node.name,
        parameters=parse_parameters(node),
        return_parameters=parse_return_parameters(node),
        body=node.body,
        visibility=Visibility[node.visibility.upper()],
        modifiers=node.modifiers,
        is_constructor=node.isConstructor,
        is_fallback=node.isFallback,
        is_receive=node.isReceive,
        state_mutability=state_mutability,
    )


def parse_modifier_definition(node: parser.Node) -> Modifier:
    return Modifier(
        name=node.name,
        parameters=parse_parameters(node),
        body=node.body,
    )


def parse_struct_definition(node: parser.Node) -> Struct:

    def parse_member(member: parser.Node) -> StructMember:
        if member.typeName.type == "ElementaryTypeName":
            type_name = member.typeName.name
        elif member.typeName.type == "UserDefinedTypeName":
            type_name = member.typeName.namePath
        else:
            raise NotImplementedError(member)
        return StructMember(
            type=type_mapping.get(type_name),
            name=member.name,
            storage_location=member.storageLocation,
        )

    return Struct(
        name=node.name,
        members=list(map(parse_member, node.members)),
    )


def parse_using_for_declaration(node: parser.Node) -> Declaration:
    return Declaration(node.typeName.name, node.libraryName)


def parse_value(typeName: parser.Node):
    """Parse value."""

    if typeName.type == "ElementaryTypeName":
        type_name = type_mapping.get(typeName.name)
    elif typeName.type == "UserDefinedTypeName":
        type_name = typeName.namePath
    elif typeName.type == "ArrayTypeName":
        if typeName.length is not None:
            warnings.warn("Fixed-size array annotation not implemented yet")
        value_type = type_mapping.get(parse_value(typeName.baseTypeName))
        type_name = type_mapping[typeName.type][value_type]
    elif typeName.type == "Mapping":
        key_type = type_mapping.get(parse_value(typeName.keyType))
        value_type = type_mapping.get(parse_value(typeName.valueType))
        type_name = type_mapping[typeName.type][key_type, value_type]
    else:
        raise NotImplementedError(ValueType)
    return type_name


def parse_variable_declaration(node: parser.Node) -> Variable:
    """Parse variable declaration."""

    assert len(node.variables) == 1
    value = node.variables[0]
    return Variable(
        name=value.name,
        type=parse_value(value.typeName),
        expression=value.expression,
        visibility=Visibility[value.visibility.upper()],
        is_state_var=value.isStateVar,
        is_declared_const=value.isDeclaredConst,
        is_indexed=value.isIndexed,
        initial_value=node.initialValue,
    )


# only in functions
def parse_return_parameters(node: parser.Node) -> List[ReturnParameter]:

    def parse_return_parameter(value: parser.Node) -> ReturnParameter:
        return ReturnParameter(
            type=parse_value(value.typeName),
            is_state_var=value.isStateVar,
            is_indexed=value.isIndexed,
            name=value.name,
            storage_location=value.get("storageLocation"),
        )

    if node.returnParameters == []:
        return []

    return list(map(parse_return_parameter, node.parameters.parameters))


def parse_parameters(node: parser.Node) -> list[Parameter]:

    def parse_parameter(value: parser.Node) -> Parameter:
        return Parameter(
            name=value.name,
            type=parse_value(value.typeName),
            is_state_var=value.isStateVar,
            is_indexed=value.isIndexed,
            storage_location=value.get("storageLocation"),
        )

    return list(map(parse_parameter, node.parameters.parameters))


@ dataclass(repr=False)
class Import(SkipDefaultFieldsReprMixin):
    """Representation of the Solidity import statement"""

    path: Union[str, Path]
    symbol_aliases: Dict = field(default_factory=dict)
    unit_alias: Optional[Dict] = None

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)


@ dataclass
class Pragma:
    """Representation of Solidity compiler directive."""

    name: str
    value: str


@ dataclass
class ContractData:
    name: str
    kind: Kind
    enums: list = field(repr=False)
    events: list[Event] = field(repr=False)
    functions: list[Function] = field(repr=False)
    modifiers: list[Modifier] = field(repr=False)
    structs: list[Struct] = field(repr=False)
    declarations: list[Declaration] = field(repr=False)
    variables: list[Variable] = field(repr=False)
    base_contracts: List[str] = field(repr=False)


def parse_contract_definition(contract: parser.Node) -> ContractData:
    """Parse contract definition."""

    base_contracts = []
    for node in contract.baseContracts:
        assert node.type == "InheritanceSpecifier"
        assert node.baseName.type == "UserDefinedTypeName"
        base_contracts.append(node.baseName.namePath)

    enums = []
    events = []
    functions = []
    modifiers = []
    variables = []
    structs = []
    declarations = []
    for node in contract.subNodes:
        if node.type == "EnumDefinition":
            enums.append(parse_enum_definition(node))
        elif node.type == "EventDefinition":
            events.append(parse_event_definition(node))
        elif node.type == "FunctionDefinition":
            functions.append(parse_function_definition(node))
        elif node.type == "ModifierDefinition":
            modifiers.append(parse_modifier_definition(node))
        elif node.type == "StateVariableDeclaration":  # ValueType
            variables.append(parse_variable_declaration(node))
        elif node.type == "StructDefinition":
            structs.append(parse_struct_definition(node))
        elif node.type == "UsingForDeclaration":
            declarations.append(parse_using_for_declaration(node))
        else:
            raise NotImplementedError(node.type)

    return ContractData(
        name=contract.name,
        kind=Kind[contract.kind.upper()],
        enums=enums,
        events=events,
        functions=functions,
        modifiers=modifiers,
        variables=variables,
        structs=structs,
        declarations=declarations,
        base_contracts=base_contracts,
    )


def parse_pragma(node: parser.Node) -> Pragma:
    return Pragma(node.name, node.value)


def parse_import(node: parser.Node) -> Import:
    return Import(node.path, node.symbolAliases, node.unitAlias)


@ dataclass
class Source:
    """Representation of the source of a Solidity contract."""

    contracts: List[Contract] = field(repr=False)
    imports: List[Import] = field(repr=False)
    pragma: Pragma = field(repr=False)


@ dataclass
class Contract:
    address: Address
    sources: List[Source] = field(repr=False)


def get_it():
    contracts = []
    for address, nodes in parsing_result.success.items():
        sources = []
        for ast in nodes:
            assert ast.type == "SourceUnit"
            imports = []
            pragmas = []
            contract_data = []
            for x in ast.children:
                if x.type == "ContractDefinition":
                    contract_data.append(parse_contract_definition(x))
                elif x.type == "PragmaDirective":
                    pragmas.append(parse_pragma(x))
                elif x.type == "ImportDirective":
                    imports.append(parse_import(x))
                else:
                    raise NotImplementedError(x.type)
            assert len(pragmas) == 1, "more than 1 pragma"
            # source = parse_source_unit(ast)
            sources.append(
                Source(contract_data, imports, pragmas[0]))
        contracts.append(Contract(address, sources))
    return contracts


# Not all contracts have all items, this works for testing
contracts = get_it()


def test():
    contract = contracts[0]
    source = contract.sources[1]
    data = source.contracts[0]

    enum = data.enums[0]
    function = data.functions[0]
    parameter = function.parameters[0]
    return_parameter = function.return_parameters[0]

    event = data.events[0]
    parameter = event.parameters[0]

    all_contracts = []
    types = set()
    enums = set()
    pub_funcs = []
    for contract in contracts:
        for source in contract.sources:
            for data in source.contracts:   # this is where it's at
                # print(contract.address, data.name, data.base_contracts)
                # if data.name == "ComptrollerV1Storage":
                #     1/0

                for function in data.functions:
                    for parameter in function.parameters:
                        types.add(parameter.type)
                    for parameter in function.return_parameters:
                        types.add(parameter.type)
                    # if function.visibility == Visibility.PUBLIC:
                    #     # pub_funcs.append(function)
                    #     print(contract.address, data.name, function.name)
                    #     print(function.parameters)
                    print(function.modifiers)

                # for modifiers in function.modifiers:  # TODO
                #     print(modifiers)

                # for enum in data.enums:  # not unique - per contract?
                #     enums.add(enum)
                for struct in data.structs:
                    for member in struct.members:
                        types.add(member.type)

                for variable in data.variables:
                    types.add(variable.type)

            # for declaration in data.declarations:
            #     print(declaration)

    print(types)
    # declaration = data.declarations[0]
    # data.structs
    # data.variables


# lets see what we get as an interface for the first contract

# visible = (Visibility.PUBLIC, Visibility.EXTERNAL)

contract = contracts[0]
interface = set()  # may overwrite functions in contracts
ext = []
for source in contract.sources:
    for data in source.contracts:
        for function in data.functions:
            if function.visibility == Visibility.PUBLIC:
                # if function.state_mutability:  # all are view
                #     print("func", function.name, function.state_mutability)
                #     # print(function.name)
                # else:
                #     print("func", function.name)
                interface.add(function.name)
            # and function.state_mutability == StateMutability.VIEW:
            if function.visibility == Visibility.EXTERNAL:
                print(function, function.state_mutability)
                ext.append(function)

        for variable in data.variables:
            if variable.visibility == Visibility.PUBLIC:
                # print("var", variable.name)
                interface.add(variable.name)

        # for item in data.structs:
        #     print("item", item)

        # for event in data.events:
            # print("event", event)


#
expected_read = [
    "_borrowGuardianPaused",
    "_mintGuardianPaused",
    "accountAssets",
    "accountMembership",
    "admin",
    "allMarkets",
    "boostManager",
    "borrowCapGuardian",
    "borrowCaps",
    "borrowState",
    "checkMembership",
    "closeFactorMantissa",
    "compRate",
    "comptrollerImplementation",
    "getAccountLiquidity",
    "getAllMarkets",
    "getAssetsIn",
    "getBoostManager",
    "getHypotheticalAccountLiquidity",
    "getTimestamp",
    "getVixAddress",
    "guardianPaused",
    "isComptroller",
    "isDeprecated",
    "isMarket",
    "lastContributorTimestamp",
    "liquidateBorrowAllowed",
    "liquidateCalculateSeizeTokens",
    "liquidationIncentiveMantissa",
    "marketInitialIndex",
    "markets",
    "maxAssets",
    "oracle",
    "pauseGuardian",
    "pendingAdmin",
    "pendingComptrollerImplementation",
    "redeemVerify",
    "rewardAccrued",
    "rewardBorrowSpeeds",
    "rewardBorrowerIndex",
    "rewardContributorSpeeds",
    "rewardReceivable",
    "rewardSpeeds",
    "rewardSupplierIndex",
    "rewardSupplySpeeds",
    "rewardUpdater",
    "seizeGuardianPaused",
    "supplyState",
    "transferGuardianPaused",
]
expected_write = []

missing_reads = set(expected_read) - interface
found_writes = interface - set(expected_read)


gotta_get = []
for f in ext:
    if f.name in missing_reads:
        gotta_get.append(f)

ext_names = {f.name for f in ext}
missing_reads - ext_names  # none missing
# ext_names - missing_reads
to_check = {}
for f in ext:
    if f.name in missing_reads:
        to_check.setdefault("in", []).append(f)
    else:
        to_check.setdefault("out", []).append(f)

# for name in missing_reads:


# should be 49 read + 40 write == 89
print(len(interface))  # 62

mut = [f for f in ext if f.state_mutability == StateMutability.VIEW]

for f in ext:
    if f.state_mutability:
        print(f)


# # failed
# mystery = "checkMembership"

# for address, response in parsing_result.success.items():
#     for item in response:
#         # if mystery in item.abi:
#         # 1/0
#         if mystery in str(item):
#             for c in item.children:
#                 if mystery in str(c):
#                     print(c.type)
#                     1/0
