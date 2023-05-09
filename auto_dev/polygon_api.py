"""Polygon API"""

from __future__ import annotations

import json
import os
import re
from dataclasses import Field, asdict, dataclass, field, fields
from enum import Enum
from functools import lru_cache
from itertools import starmap
from pathlib import Path
from pprint import pprint
from typing import Any, Callable, Dict, Iterable, List, Optional, Union, cast
from urllib.parse import urlparse

import requests
from solidity_parser import parser  # type: ignore
from typing_extensions import TypeGuard


# utility functions and classes
def map_starmap(func: Callable[..., Any], iterable_of_kwargs: Iterable[Dict[str, Any]]) -> map:
    """Map an iterable of keyword arguments onto a callable."""

    return map(lambda kv: func(**kv), iterable_of_kwargs)


def clean_code(source_code: str) -> str:
    """Replace double curly braces for single in the solidity source code for json.loads"""

    return source_code.replace("{{", "{").replace("}}", "}")


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""

    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def keys_to_snake_case(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all keys to snake_case."""

    return dict(zip(map(camel_to_snake, data.keys()), data.values()))


class Address:
    """Hexadecimal blockchain address."""

    HEX_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

    def __init__(self, value: str) -> None:
        if not Address.is_valid_hex(value):
            raise ValueError(f"Invalid hexadecimal address: {value}")
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Address('{self._value}')"

    @staticmethod
    def is_valid_hex(value: str) -> bool:
        """Check that the address is a valid hexadecimal string representation."""

        return isinstance(value, str) and Address.HEX_REGEX.match(value) is not None


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


# Enums
class ABIType(EnumStrAndReprMixin, Enum):
    """All possible types of elements of an Application Binary Interface (ABI)."""

    FUNCTION = "function"
    CONSTRUCTOR = "constructor"
    EVENT = "event"
    FALLBACK = "fallback"
    RECEIVE = "receive"


class StateMutability(EnumStrAndReprMixin, Enum):
    """State mutability of solidity function calls."""

    PURE = "pure"
    VIEW = "view"
    NONPAYABLE = "nonpayable"
    PAYABLE = "payable"


# Polygon API Request Response
@dataclass
class Request:
    """Paramaters for the PolygonAPI reguest."""

    module: str
    action: str
    address: Address
    apikey: str


@dataclass
class Response:
    """Return values of the PolygonAPI response."""

    status: str
    message: str
    result: str = field(repr=False)
    action: Contract.Action

    def __post_init__(self):
        self.status = self.status == "1"
        if not self.status:  # time to panic!
            raise ValueError(f"PANIC: {self.result}")


# ABI specific
@dataclass
class ABI:
    """Representation of the Application Binary Interface (ABI)."""

    methods: List[Method]


@dataclass(repr=False)
class Method(SkipDefaultFieldsReprMixin):
    """Representation of a smart contract ABI element."""

    type: ABIType
    inputs: Optional[List[Input]] = None  # optional for constructor
    name: Optional[str] = None
    outputs: Optional[List[Output]] = None
    state_mutability: Optional[StateMutability] = None
    anonymous: Optional[bool] = None  # only for events

    def __post_init__(self):
        self.type = ABIType[str(self.type).upper()]
        if (attr := self.state_mutability) is not None:
            self.state_mutability = StateMutability[attr.upper()]
        if self.inputs is not None:
            inputs = map(keys_to_snake_case, self.inputs)
            self.inputs = list(map_starmap(Input, inputs))
        if self.outputs is not None:
            outputs = map(keys_to_snake_case, self.outputs)
            self.outputs = list(map_starmap(Output, outputs))


@dataclass(repr=False)
class Input(SkipDefaultFieldsReprMixin):
    """Representation of inputs an ABI type takes."""

    # both elementary and complex types (uintX, enum, function, etc.)
    type: str
    name: Optional[str] = None
    # only for events
    indexed: Optional[bool] = field(repr=False, default=None)
    # only for functions
    components: Optional[List[Input]] = field(repr=False, default=None)
    internal_type: Optional[str] = field(repr=False, default=None)
    base_type: Optional[str] = field(repr=False, default=None)


@dataclass(repr=False)
class Output(SkipDefaultFieldsReprMixin):
    """Representation of output an ABI type returns."""

    internal_type: str
    type: str
    name: str = ""


# Contract specific
@dataclass
class ContractSourceCode:
    """Representation of the smart contract source code."""

    data: List[ContractData]


@dataclass(repr=False)
class ContractData(SkipDefaultFieldsReprMixin):  # noqa
    """Representation of the idividual contract's data."""

    source_code: SourceCode = field(repr=False)
    abi: Optional[ABI] = field(repr=False, default=None)
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

    def __post_init__(self):
        if self.optimization_used is not None:
            self.optimization_used = self.optimization_used == "1"
        if self.proxy is not None:
            self.proxy = self.proxy == "1"
        if self.runs is not None:
            self.runs = int(self.runs)
        if self.abi is not None:
            method_data = map(keys_to_snake_case, json.loads(self.abi))
            self.abi = ABI(list(map_starmap(Method, method_data)))
        code = clean_code(self.source_code)
        self.source_code = SourceCode(**json.loads(code))


@dataclass
class SourceCode(SkipDefaultFieldsReprMixin):
    """Representation of the Solidity source code object."""

    language: str
    version: Optional[str] = field(repr=False, default=None)
    settings: Optional[Dict] = field(repr=False, default=None)
    sources: Optional[List[Source]] = field(repr=False, default=None)

    def __post_init__(self):
        if self.sources is not None:
            self.sources = list(starmap(Source, self.sources.items()))


@dataclass
class Source:
    """Representation of the source of a Solidity contract."""

    path: Union[str, Path]
    code: str = field(repr=False, init=False)
    node: parser.Node = field(repr=False, init=False)
    imports: List[Import] = field(init=False, repr=False)
    pragmas: List[Pragma] = field(init=False, repr=False)

    def __init__(self, path: str, data: Dict):
        self.path = Path(path)
        self.code = data["content"]
        self.node = parser.parse(self.code)
        obj = parser.objectify(self.node)
        self.pragmas = list(map_starmap(Pragma, obj.pragmas))
        imports = map(keys_to_snake_case, obj.imports)
        self.imports = list(map_starmap(Import, imports))
        self.contracts = obj.contracts  # not included in asdict

    def pprint(self):
        """Pretty print the contract."""

        pprint(self.node)


@ dataclass
class Import:
    """Representation of the Solidity import statement"""

    path: Union[str, Path]
    type: str = "ImportDirective"
    symbol_aliases: Dict = field(default_factory=dict)
    unit_alias: Optional[Dict] = None

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)


@ dataclass
class Pragma:
    """Representation of Solidity compiler directives."""

    name: str
    value: str
    type: str = "PragmaDirective"


def process_response(response: Response) -> Union[ABI, ContractSourceCode]:
    """Process a PolygonAPI response."""

    if response.action == Contract.Action.GET_ABI:
        method_data = map(keys_to_snake_case, json.loads(response.result))
        return ABI(list(map_starmap(Method, method_data)))
    if response.action == Contract.Action.GET_SOURCE_CODE:
        result = map(keys_to_snake_case, cast(List[Dict], response.result))
        return ContractSourceCode(list(map_starmap(ContractData, result)))
    raise ValueError(f"Incorrect response type: {response}")


class Contract:
    """Representation of the smart contract module."""

    module = "contract"

    def __init__(self, api: PolygonAPI):
        self.api = api

    class Action(EnumStrAndReprMixin, Enum):
        """Contract API call action."""

        GET_ABI = "getabi"
        GET_SOURCE_CODE = "getsourcecode"
        GET_CONTRACT_CREATION = "getcontractcreation"

    @ lru_cache()
    def get_contract_data(self, *addresses: str, action: Action) -> dict[Address, Response]:
        """Request smart contract data from the API."""

        responses = {}
        for address in map(Address, addresses):
            fields = Request(self.module, action.value,
                             address, self.api.api_key)
            response = requests.get(
                f"{self.api.api_endpoint.geturl()}/",
                params=asdict(fields),
                timeout=self.api.request_timeout,
            )
            responses[address] = Response(**response.json(), action=action)
            print(f"Obtained {action} for {address}")
        return responses

    def get_abi(self, *addresses: str) -> List[ABI]:
        """Get smart contract Application Binary Interface (ABI)."""

        responses = self.get_contract_data(
            *addresses, action=Contract.Action.GET_ABI)
        abis = list(map(process_response, responses.values()))
        return cast(List[ABI], abis)

    def get_source_code(self, *addresses: str) -> List[ContractSourceCode]:
        """Get smart contract source code."""

        responses = self.get_contract_data(
            *addresses, action=Contract.Action.GET_SOURCE_CODE)
        contract_source_code = list(map(process_response, responses.values()))
        return cast(List[ContractSourceCode], contract_source_code)

    def get_contract_creation(self, *addresses: str):
        """Get smart contract creation details."""

        raise NotImplementedError()

    def verify_source_code(self, *addresses: str):
        """Verify smart contract source code."""

        raise NotImplementedError()

    def check_verify_status(self, *addresses: str):
        """Check smart contract verification status."""

        raise NotImplementedError()

    def verify_proxy_contract(self, *addresses: str):
        """Verify proxy contract."""

        raise NotImplementedError()


class PolygonAPI:
    """PolygonAPI"""

    api_endpoint = urlparse("https://api.polygonscan.com/api")
    request_timeout = 3

    def __init__(self, polygon_api_key: Optional[str] = None):
        api_key = polygon_api_key or os.environ.get("POLYGONSCAN_API_KEY")
        if not api_key:
            raise ValueError("'POLYGONSCAN_API_KEY' is required")
        self.api_key = str(api_key)
        self.contract = Contract(self)
