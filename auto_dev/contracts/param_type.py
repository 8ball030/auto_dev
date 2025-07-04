"""Module contains the ParamType class, which represents the type of a parameter in solidity."""

from enum import Enum


class ParamType(Enum):
    """Class to represent the type of a parameter in solidity."""

    ADDRESS = "address"
    ADDRESS_ARRAY = "address[]"
    BOOL = "bool"
    BYTES = "bytes"
    BYTES_ARRAY = "bytes[]"
    BYTES32 = "bytes32"
    BYTES32_ARRAY = "bytes32[]"
    BYTES32_ARRAY_ARRAY = "bytes32[][]"
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    INT128 = "int128"
    INT256 = "int256"
    INT256_ARRAY = "int256[]"
    STRING_ARRAY = "string[]"
    TUPLE = "tuple"
    UINT8 = "uint8"
    UINT8_ARRAY = "uint8[]"
    UINT16 = "uint16"
    UINT24 = "uint24"
    UINT32 = "uint32"
    UINT32_ARRAY = "uint32[]"
    UINT64 = "uint64"
    UINT64_ARRAY = "uint64[]"
    UINT80 = "uint80"
    UINT128 = "uint128"
    UINT256 = "uint256"
    UINT256_ARRAY = "uint256[]"
    UINT256_2_ARRAY = "uint256[2]"
    UINT256_3_ARRAY = "uint256[3]"
    INT80_ARRAY = "int80[]"
    STRING = "string"
    TUPLE_ARRAY = "tuple[]"
    INT24 = "int24"
    BYTES4 = "bytes4"
    BOOL_ARRAY = "bool[]"
