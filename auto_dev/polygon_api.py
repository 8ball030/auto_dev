from __future__ import annotations

import difflib
import json
import os
import re
from dataclasses import Field, asdict, dataclass, field, fields
from enum import Enum
from functools import cached_property, lru_cache
from itertools import starmap, zip_longest
from pathlib import Path
from pprint import pprint
from typing import Any, Callable, Iterable, Optional, TypeGuard, Union, cast
from urllib.parse import urlparse

import requests
from solidity_parser import parser  # type: ignore


# utility functions and classes
def map_starmap(func: Callable[..., Any], iterable_of_kwargs: Iterable[dict]) -> map:
    return map(lambda kv: func(**kv), iterable_of_kwargs)


def clean_code(s: str) -> str:  # else cannot use json.loads
    return s.replace("{{", "{").replace("}}", "}")


class Address:
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
        return isinstance(value, str) and Address.HEX_REGEX.match(value) is not None


class EnumStrAndReprMixin:
    def __str__(self):
        return self.name

    __repr__ = __str__


@dataclass
class SkipDefaultFieldsReprMixin:
    def __repr__(self) -> str:
        def condition(f: Field[Any]) -> TypeGuard[bool]:
            return f.repr and getattr(self, f.name) not in (f.default, "")

        def display(f) -> str:
            return f"{f.name}={getattr(self, f.name)}"

        node_repr = ", ".join(map(display, filter(condition, fields(self))))
        return f"{self.__class__.__name__}({node_repr})"


# Enums
class ABIType(EnumStrAndReprMixin, Enum):
    FUNCTION = "function"
    CONSTRUCTOR = "constructor"
    EVENT = "event"
    FALLBACK = "fallback"
    RECEIVE = "receive"


class StateMutability(EnumStrAndReprMixin, Enum):
    PURE = "pure"
    VIEW = "view"
    NONPAYABLE = "nonpayable"
    PAYABLE = "payable"


# Polygon API Request Response
@dataclass
class Request:
    module: str
    action: str
    address: Address
    apikey: str


@dataclass
class Response:
    status: str
    message: str
    result: str = field(repr=False)
    action: Contract.Action

    def __post_init__(self):
        self.status == self.status == "1"
        if not self.status:  # time to panic!
            raise ValueError(f"PANIC: {self.result}")


# ABI specific
@dataclass
class ABI:
    methods: list[Method]


@dataclass(repr=False)
class Method(SkipDefaultFieldsReprMixin):
    type: ABIType
    inputs: Optional[list[Input]] = None  # optional for constructor
    name: Optional[str] = None
    outputs: Optional[list] = None
    stateMutability: Optional[StateMutability] = None
    anonymous: Optional[bool] = None  # only for events

    def __post_init__(self):
        self.type = ABIType[self.type.upper()]
        if (attr := self.stateMutability) is not None:
            self.stateMutability = StateMutability[attr.upper()]
        if self.inputs is not None:
            self.inputs = list(starmap(Input, self.inputs))


@dataclass(repr=False)
class Input(SkipDefaultFieldsReprMixin):
    # both elementary and complex types (uintX, enum, function, etc.)
    type: str
    name: Optional[str] = None
    # only for events
    indexed: Optional[bool] = field(repr=False, default=None)
    # only for functions
    components: Optional[list[Input]] = field(repr=False, default=None)
    internalType: Optional[str] = field(repr=False, default=None)
    baseType: Optional[str] = field(repr=False, default=None)


# Contract data specific
@dataclass
class ContractSourceCode:
    data: list[ContractData]


@dataclass(repr=False)
class ContractData(SkipDefaultFieldsReprMixin):
    SourceCode: SourceCode = field(repr=False)
    ABI: Optional[ABI] = field(repr=False, default=None)
    ContractName: Optional[str] = None
    CompilerVersion: Optional[str] = field(repr=False, default=None)
    OptimizationUsed: Optional[bool] = field(repr=False, default=None)
    Runs: Optional[int] = field(repr=False, default=None)
    ConstructorArguments: Optional[str] = field(repr=False, default=None)
    EVMVersion: Optional[str] = field(repr=False, default=None)
    Library: Optional[str] = field(repr=False, default=None)
    LicenseType: Optional[str] = field(repr=False, default=None)
    Proxy: Optional[bool] = None
    Implementation: Optional[str] = field(repr=False, default=None)
    SwarmSource: Optional[str] = field(repr=False, default=None)
    SourceCodeHash: Optional[str] = field(repr=False, default=None)
    SourceCodeMetaData: Optional[str] = field(repr=False, default=None)
    AST: Optional[str] = field(repr=False, default=None)
    SourceList: Optional[list[str]] = field(repr=False, default=None)
    DeveloperDoc: Optional[str] = field(repr=False, default=None)
    UserDoc: Optional[str] = field(repr=False, default=None)

    def __post_init__(self):
        if self.OptimizationUsed is not None:
            self.OptimizationUsed = self.OptimizationUsed == "1"
        if self.Proxy is not None:
            self.Proxy = self.Proxy == "1"
        if self.Runs is not None:
            self.Runs == int(self.Runs)
        if self.ABI is not None:  # most to post_init ABI
            self.ABI = ABI(list(map_starmap(Method, json.loads(self.ABI))))
        code = clean_code(self.SourceCode)
        self.SourceCode = SourceCode(**json.loads(code))


@dataclass
class SourceCode(SkipDefaultFieldsReprMixin):
    language: str
    version: Optional[str] = field(repr=False, default=None)
    settings: Optional[dict] = field(repr=False, default=None)
    sources: Optional[list[Source]] = field(repr=False, default=None)

    def __post_init__(self):
        if self.sources is not None:
            self.sources = list(starmap(Source, self.sources.items()))


@dataclass
class Source:
    path: Union[str, Path]
    code: str = field(repr=False, init=False)
    node: dict = field(repr=False, init=False)
    imports: list[Import] = field(init=False, repr=False)
    pragmas: list[Pragma] = field(init=False, repr=False)

    def pprint(self):
        pprint(self.node)

    def __init__(self, path: str, data: dict):
        self.path = Path(path)
        self.code = data["content"]
        node = parser.parse(self.code)
        obj = parser.objectify(node)
        self.node = dict(node)
        self.pragmas = list(map_starmap(Pragma, obj.pragmas))
        self.imports = list(map_starmap(Import, obj.imports))
        self.contracts = obj.contracts  # not included in asdict


@dataclass
class Import:
    path: Union[str, Path]
    type: str = "ImportDirective"
    symbolAliases: dict = field(default_factory=dict)
    unitAlias: Optional[dict] = None

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)


@dataclass
class Pragma:
    name: str
    value: str
    type: str = "PragmaDirective"


def process_response(response: Response) -> Union[ABI, ContractSourceCode]:
    if response.action == Contract.Action.GET_ABI:
        return ABI(list(map_starmap(Method, json.loads(response.result))))
    elif response.action == Contract.Action.GET_SOURCE_CODE:
        result = cast(list[dict], response.result)
        return ContractSourceCode(list(map_starmap(ContractData, result)))
    raise ValueError(f"Incorrect response type: {response}")


class Contract:

    module = "contract"

    def __init__(self, api: PolygonAPI):
        self.api = api

    class Action(EnumStrAndReprMixin, Enum):
        GET_ABI = "getabi"
        GET_SOURCE_CODE = "getsourcecode"
        GET_CONTRACT_CREATION = "getcontractcreation"

    @lru_cache()
    def get_contract_data(
        self, *addresses: str, action: Action
    ) -> dict[Address, Response]:
        responses = {}
        for address in map(Address, addresses):
            fields = Request(self.module, action.value, address, self.api.api_key)
            url = f"{self.api.api_endpoint.geturl()}/"
            response = requests.get(url, params=asdict(fields))
            responses[address] = Response(**response.json(), action=action)
            print(f"Obtained {action} for {address}")
        return responses

    def get_abi(self, *addresses: str) -> list[ABI]:
        responses = self.get_contract_data(*addresses, action=Contract.Action.GET_ABI)
        abis = list(map(process_response, responses.values()))
        return cast(list[ABI], abis)

    def get_source_code(self, *addresses: str) -> list[ContractSourceCode]:
        responses = self.get_contract_data(
            *addresses, action=Contract.Action.GET_SOURCE_CODE
        )
        contract_source_code = list(map(process_response, responses.values()))
        return cast(list[ContractSourceCode], contract_source_code)

    def get_contract_creation(self, *addresses: str):
        raise NotImplementedError()

    def verify_source_code(self, *addresses: str):
        raise NotImplementedError()

    def check_verify_status(self, *addresses: str):
        raise NotADirectoryError()

    def verify_proxy_contract(self, *addresses: str):
        raise NotADirectoryError()


class PolygonAPI:

    api_endpoint = urlparse("https://api.polygonscan.com/api")

    def __init__(self, polygon_api_key: Optional[str] = None):
        api_key = polygon_api_key or os.environ.get("POLYGONSCAN_API_KEY")
        if not api_key:
            raise ValueError("'POLYGONSCAN_API_KEY' is required")
        self.api_key = str(api_key)
        self.contract = Contract(self)
