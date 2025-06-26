"""Utils for the contracts."""

from aea.crypto.base import Address

from auto_dev.contracts.param_type import ParamType


SOLIDITY_TYPE_TO_PYTHON_TYPE = {
    "address": Address,
    "bool": bool,
    "uint256": int,
    "int128": int,
}

SOLIDITY_TO_PYTHON_TYPES = {
    "address": "str",
    "bool": "bool",
    "bytes": "str",
    "bytes32": "str",
    "bytes4": "str",
    "int16": "int",
    "int8": "int",
    "string": "str",
    "tuple": "tuple",
    "uint256": "int",
    "uint80": "int",
}


PARAM_TO_STR_MAPPING = {
    ParamType.ADDRESS: "Address",
    ParamType.ADDRESS_ARRAY: "List[Address]",
    ParamType.BOOL: "bool",
    ParamType.BYTES: "str",
    ParamType.BYTES_ARRAY: "List[str]",
    ParamType.BYTES4: "str",
    ParamType.BYTES32: "str",
    ParamType.BYTES32_ARRAY: "List[str]",
    ParamType.BYTES32_ARRAY_ARRAY: "List[List[str]]",
    ParamType.INT8: "int",
    ParamType.INT16: "int",
    ParamType.INT24: "int",
    ParamType.INT32: "int",
    ParamType.INT64: "int",
    ParamType.INT80_ARRAY: "List[int]",
    ParamType.INT128: "int",
    ParamType.INT256: "int",
    ParamType.INT256_ARRAY: "List[int]",
    ParamType.STRING: "str",
    ParamType.STRING_ARRAY: "List[str]",
    ParamType.TUPLE: "tuple",
    ParamType.TUPLE_ARRAY: "Tuple[...]",
    ParamType.UINT8: "int",
    ParamType.UINT8_ARRAY: "List[int]",
    ParamType.UINT16: "int",
    ParamType.UINT24: "int",
    ParamType.UINT32: "int",
    ParamType.UINT32_ARRAY: "List[int]",
    ParamType.UINT64: "int",
    ParamType.UINT64_ARRAY: "List[int]",
    ParamType.UINT80: "int",
    ParamType.UINT128: "int",
    ParamType.UINT256: "int",
    ParamType.UINT256_ARRAY: "List[int]",
    ParamType.UINT256_2_ARRAY: "List[int]",
    ParamType.UINT256_3_ARRAY: "List[int]",
    ParamType.BOOL_ARRAY: "List[bool]",
}


PYTHON_KEYWORDS = [
    "from",
    "type",
    "global",
    "nonlocal",
    "assert",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "if",
    "import",
    "lambda",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
]


def keyword_to_safe_name(name: str) -> str:
    """Convert a keyword to a safe name."""
    return f"{name}_" if name in PYTHON_KEYWORDS else name


def safe_name_to_keyword(name: str) -> str:
    """Convert a safe name to a keyword."""
    return name[:-1] if name in PYTHON_KEYWORDS else name
