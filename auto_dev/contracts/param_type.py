"""Module contains the ParamType class, which represents the type of a parameter in solidity."""

from enum import Enum


class ParamType(Enum):
    """Class to represent the type of a parameter in solidity."""

    ADDRESS = "address"
    BOOL = "bool"
    UINT256 = "uint256"
    UNINT64 = "uint64"
    UNINT32 = "uint32"
    UINT8 = "uint8"
    UINT8_ARRAY = "uint8[]"
    UINT16 = "uint16"
    UINT24 = "uint24"
    UINT128 = "uint128"
    INT128 = "int128"
    INT256 = "int256"
    BYTES32 = "bytes32"
    UINT80 = "uint80"
    TUPLE = "tuple"
    UINT256_ARRAY = "uint256[]"
    UINT64_ARRAY = "uint64[]"
    INT256_ARRAY = "int256[]"
    UINT256_2_ARRAY = "uint256[2]"
    UINT256_3_ARRAY = "uint256[3]"
    INT80_ARRAY = "int80[]"
    ADDRESS_ARRAY = "address[]"
    STRING = "string"
    STRING_ARRAY = "string[]"
    TUPLE_ARRAY = "tuple[]"
    UINT32_ARRAY = "uint32[]"
    INT24 = "int24"
    INT16 = "int16"
    BYTES4 = "bytes4"
    BYTES = "bytes"
    BYTES_ARRAY = "bytes[]"
    BYTES32_ARRAY_ARRAY = "bytes32[][]"
