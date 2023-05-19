"""
Representations of elementary solidity types
"""

import typing
import re
from eth_utils import to_checksum_address


# TODO:
# To make it JSON serializable one would need to introduce a custom encoder / decoder


class IntFactory:
    """Factory for creating signed integer classes."""

    @staticmethod
    def create_int_class(bits: int) -> type:
        """Create a new signed integer class with the specified number of bits."""

        if not isinstance(bits, int) or bits <= 0:
            raise ValueError("Number of bits must be a positive integer.")

        class SimpleRepr(type):

            def __repr__(cls):
                return f"{cls.__name__}{bits}"

        class Int(metaclass=SimpleRepr):
            """Signed integer class."""

            MIN_VALUE = -(2**(bits-1))
            MAX_VALUE = 2**(bits-1) - 1

            def __init__(self, value: int) -> None:
                if not Int.is_valid(value):
                    raise ValueError(f"Invalid int{bits} value: {value}")
                self._value = value

            def __int__(self) -> int:
                return self._value

            def __str__(self) -> str:
                return str(self._value)

            def __repr__(self) -> str:
                return f"{self.__class__.__name__}{bits}({self._value})"

            # def __module__(self) -> str:
            #     return __module__

            @staticmethod
            def is_valid(value: int) -> bool:
                """Check that the value is a valid int{bits}."""

                return isinstance(value, int) and Int.MIN_VALUE <= value <= Int.MAX_VALUE

        return Int


class UintFactory:
    """Factory for creating unsigned integer classes."""

    @staticmethod
    def create_uint_class(bits: int) -> type:
        """Create a new unsigned integer class with the specified number of bits."""

        if not isinstance(bits, int) or bits <= 0:
            raise ValueError("Number of bits must be a positive integer.")

        class SimpleRepr(type):

            def __repr__(cls):
                return f"{cls.__name__}{bits}"

        class Uint(metaclass=SimpleRepr):
            """Unsigned integer class."""

            MIN_VALUE = 0
            MAX_VALUE = 2**bits - 1

            def __init__(self, value: int) -> None:
                if not Uint.is_valid(value):
                    raise ValueError(f"Invalid uint{bits} value: {value}")
                self._value = value

            def __int__(self) -> int:
                return self._value

            def __str__(self) -> str:
                return str(self._value)

            def __repr__(self) -> str:
                return f"{self.__class__.__name__}{bits}({self._value})"

            # def __module__(self) -> str:
            #     return __module__

            @staticmethod
            def is_valid(value: int) -> bool:
                """Check that the value is a valid uint{bits}."""

                return isinstance(value, int) and Uint.MIN_VALUE <= value <= Uint.MAX_VALUE

        return Uint


class BytesFactory:
    """Factory for creating fixed-size byte array classes."""

    @staticmethod
    def create_fixed_byte_array(size: int):

        class SimpleRepr(type):

            def __repr__(cls):
                return f"{cls.__name__}{size}"

        class Bytes(metaclass=SimpleRepr):
            def __init__(self, value):
                if not isinstance(value, bytes) or len(value) != size:
                    raise ValueError(f"Invalid fixed-size byte array: {value}")
                self._value = value

            def __bytes__(self):
                return bytes(self._value)

            def __str__(self):
                return self._value.hex()

            def __repr__(self):
                return f"{self.__class__.__name__}('{int(bytes(self))}')"

            def __eq__(self, other):
                if isinstance(other, FixedByteArray):
                    return self._value == other._value
                return False

        return Bytes


# Booleans:
# https://docs.soliditylang.org/en/latest/types.html#booleans
# already exist in python: bool


# Integers:
# https://docs.soliditylang.org/en/latest/types.html#integers


Int8 = IntFactory.create_int_class(8)
Int16 = IntFactory.create_int_class(16)
Int24 = IntFactory.create_int_class(24)
Int32 = IntFactory.create_int_class(32)
Int40 = IntFactory.create_int_class(40)
Int48 = IntFactory.create_int_class(48)
Int56 = IntFactory.create_int_class(56)
Int64 = IntFactory.create_int_class(64)
Int72 = IntFactory.create_int_class(72)
Int80 = IntFactory.create_int_class(80)
Int88 = IntFactory.create_int_class(88)
Int96 = IntFactory.create_int_class(96)
Int104 = IntFactory.create_int_class(104)
Int112 = IntFactory.create_int_class(112)
Int120 = IntFactory.create_int_class(120)
Int128 = IntFactory.create_int_class(128)
Int136 = IntFactory.create_int_class(136)
Int144 = IntFactory.create_int_class(144)
Int152 = IntFactory.create_int_class(152)
Int160 = IntFactory.create_int_class(160)
Int168 = IntFactory.create_int_class(168)
Int176 = IntFactory.create_int_class(176)
Int184 = IntFactory.create_int_class(184)
Int192 = IntFactory.create_int_class(192)
Int200 = IntFactory.create_int_class(200)
Int208 = IntFactory.create_int_class(208)
Int216 = IntFactory.create_int_class(216)
Int224 = IntFactory.create_int_class(224)
Int232 = IntFactory.create_int_class(232)
Int240 = IntFactory.create_int_class(240)
Int248 = IntFactory.create_int_class(248)
Int256 = IntFactory.create_int_class(256)
Int = Int256  # alias


Uint8 = UintFactory.create_uint_class(8)
Uint16 = UintFactory.create_uint_class(16)
Uint24 = UintFactory.create_uint_class(24)
Uint32 = UintFactory.create_uint_class(32)
Uint40 = UintFactory.create_uint_class(40)
Uint48 = UintFactory.create_uint_class(48)
Uint56 = UintFactory.create_uint_class(56)
Uint64 = UintFactory.create_uint_class(64)
Uint72 = UintFactory.create_uint_class(72)
Uint80 = UintFactory.create_uint_class(80)
Uint88 = UintFactory.create_uint_class(88)
Uint96 = UintFactory.create_uint_class(96)
Uint104 = UintFactory.create_uint_class(104)
Uint112 = UintFactory.create_uint_class(112)
Uint120 = UintFactory.create_uint_class(120)
Uint128 = UintFactory.create_uint_class(128)
Uint136 = UintFactory.create_uint_class(136)
Uint144 = UintFactory.create_uint_class(144)
Uint152 = UintFactory.create_uint_class(152)
Uint160 = UintFactory.create_uint_class(160)
Uint168 = UintFactory.create_uint_class(168)
Uint176 = UintFactory.create_uint_class(176)
Uint184 = UintFactory.create_uint_class(184)
Uint192 = UintFactory.create_uint_class(192)
Uint200 = UintFactory.create_uint_class(200)
Uint208 = UintFactory.create_uint_class(208)
Uint216 = UintFactory.create_uint_class(216)
Uint224 = UintFactory.create_uint_class(224)
Uint232 = UintFactory.create_uint_class(232)
Uint240 = UintFactory.create_uint_class(240)
Uint248 = UintFactory.create_uint_class(248)
Uint256 = UintFactory.create_uint_class(256)
Uint = Uint256  # alias


# Fixed point numbers: fixed and ufixed
# Not implemented since not fully supported in Solidity yet
# https://docs.soliditylang.org/en/latest/types.html#fixed-point-numbers


# address:
# https://docs.soliditylang.org/en/latest/types.html#address


class SimpleRepr(type):

    def __repr__(cls):
        return f"{cls.__name__}"


class Address(metaclass=SimpleRepr):
    """Hexadecimal blockchain address."""

    HEX_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

    def __init__(self, value: str) -> None:
        if not Address.is_valid_hex(value):
            raise ValueError(f"Invalid hexadecimal address: {value}")
        self._value = to_checksum_address(value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Address('{self._value}')"

    @staticmethod
    def is_valid_hex(value: str) -> bool:
        """Check that the address is a valid hexadecimal string representation."""

        return isinstance(value, str) and Address.HEX_REGEX.match(value) is not None


# Fixed-size byte arrays:
# https://docs.soliditylang.org/en/latest/types.html#fixed-size-byte-arrays


Bytes1 = BytesFactory.create_fixed_byte_array(1)
Bytes2 = BytesFactory.create_fixed_byte_array(2)
Bytes3 = BytesFactory.create_fixed_byte_array(3)
Bytes4 = BytesFactory.create_fixed_byte_array(4)
Bytes5 = BytesFactory.create_fixed_byte_array(5)
Bytes6 = BytesFactory.create_fixed_byte_array(6)
Bytes7 = BytesFactory.create_fixed_byte_array(7)
Bytes8 = BytesFactory.create_fixed_byte_array(8)
Bytes9 = BytesFactory.create_fixed_byte_array(9)
Bytes10 = BytesFactory.create_fixed_byte_array(10)
Bytes11 = BytesFactory.create_fixed_byte_array(11)
Bytes12 = BytesFactory.create_fixed_byte_array(12)
Bytes13 = BytesFactory.create_fixed_byte_array(13)
Bytes14 = BytesFactory.create_fixed_byte_array(14)
Bytes15 = BytesFactory.create_fixed_byte_array(15)
Bytes16 = BytesFactory.create_fixed_byte_array(16)
Bytes17 = BytesFactory.create_fixed_byte_array(17)
Bytes18 = BytesFactory.create_fixed_byte_array(18)
Bytes19 = BytesFactory.create_fixed_byte_array(19)
Bytes20 = BytesFactory.create_fixed_byte_array(20)
Bytes21 = BytesFactory.create_fixed_byte_array(21)
Bytes22 = BytesFactory.create_fixed_byte_array(22)
Bytes23 = BytesFactory.create_fixed_byte_array(23)
Bytes24 = BytesFactory.create_fixed_byte_array(24)
Bytes25 = BytesFactory.create_fixed_byte_array(25)
Bytes26 = BytesFactory.create_fixed_byte_array(26)
Bytes27 = BytesFactory.create_fixed_byte_array(27)
Bytes28 = BytesFactory.create_fixed_byte_array(28)
Bytes29 = BytesFactory.create_fixed_byte_array(29)
Bytes30 = BytesFactory.create_fixed_byte_array(30)
Bytes31 = BytesFactory.create_fixed_byte_array(31)
Bytes32 = BytesFactory.create_fixed_byte_array(32)


# dynamically-sized byte array
# https://docs.soliditylang.org/en/latest/types.html#dynamically-sized-byte-array
# already exists in python: bytes

# address literals
# https://docs.soliditylang.org/en/latest/types.html#address-literals


# Rational and integer literals
# https://docs.soliditylang.org/en/latest/types.html#rational-and-integer-literals


# string literals and types
# https://docs.soliditylang.org/en/latest/types.html#string-literals-and-types
# already exists in python: str

# unicode literals
# https://docs.soliditylang.org/en/latest/types.html#unicode-literals


# hexadecimal literal:
# https://docs.soliditylang.org/en/latest/types.html#hexadecimal-literals

# enum
# https://docs.soliditylang.org/en/latest/types.html#enums
# already exists in python: enum.Enum


# References types:
# Data location
# https://docs.soliditylang.org/en/latest/types.html#data-location

# Arrays
# https://docs.soliditylang.org/en/latest/types.html#arrays


# Mapping
# https://docs.soliditylang.org/en/latest/types.html#mapping-types
# already exists in python: Typing.Dict


# function
# https://docs.soliditylang.org/en/latest/types.html#function-types
# already exists in python: def


# Type mapping using when parsing Solidity code


class TypeMapping(dict):

    def get(self, item: typing.Any):
        if item in self:
            return self[item]
        if isinstance(item, str):
            return typing.ForwardRef(item)
        return item


type_mapping = TypeMapping({
    "bool": bool,

    "int8": Int8,
    "int16": Int16,
    "int24": Int24,
    "int32": Int32,
    "int40": Int40,
    "int48": Int48,
    "int56": Int56,
    "int64": Int64,
    "int72": Int72,
    "int80": Int80,
    "int88": Int88,
    "int96": Int96,
    "int104": Int104,
    "int112": Int112,
    "int120": Int120,
    "int128": Int128,
    "int136": Int136,
    "int144": Int144,
    "int152": Int152,
    "int160": Int160,
    "int168": Int168,
    "int176": Int176,
    "int184": Int184,
    "int192": Int192,
    "int200": Int200,
    "int208": Int208,
    "int216": Int216,
    "int224": Int224,
    "int232": Int232,
    "int240": Int240,
    "int248": Int248,
    "int256": Int256,
    "int": Int,

    "uint8": Uint8,
    "uint16": Uint16,
    "uint24": Uint24,
    "uint32": Uint32,
    "uint40": Uint40,
    "uint48": Uint48,
    "uint56": Uint56,
    "uint64": Uint64,
    "uint72": Uint72,
    "uint80": Uint80,
    "uint88": Uint88,
    "uint96": Uint96,
    "uint104": Uint104,
    "uint112": Uint112,
    "uint120": Uint120,
    "uint128": Uint128,
    "uint136": Uint136,
    "uint144": Uint144,
    "uint152": Uint152,
    "uint160": Uint160,
    "uint168": Uint168,
    "uint176": Uint176,
    "uint184": Uint184,
    "uint192": Uint192,
    "uint200": Uint200,
    "uint208": Uint208,
    "uint216": Uint216,
    "uint224": Uint224,
    "uint232": Uint232,
    "uint240": Uint240,
    "uint248": Uint248,
    "uint256": Uint256,
    "uint": Uint,

    "bytes1": Bytes1,
    "bytes2": Bytes2,
    "bytes3": Bytes3,
    "bytes4": Bytes4,
    "bytes5": Bytes5,
    "bytes6": Bytes6,
    "bytes7": Bytes7,
    "bytes8": Bytes8,
    "bytes9": Bytes9,
    "bytes10": Bytes10,
    "bytes11": Bytes11,
    "bytes12": Bytes12,
    "bytes13": Bytes13,
    "bytes14": Bytes14,
    "bytes15": Bytes15,
    "bytes16": Bytes16,
    "bytes17": Bytes17,
    "bytes18": Bytes18,
    "bytes19": Bytes19,
    "bytes20": Bytes20,
    "bytes21": Bytes21,
    "bytes22": Bytes22,
    "bytes23": Bytes23,
    "bytes24": Bytes24,
    "bytes25": Bytes25,
    "bytes26": Bytes26,
    "bytes27": Bytes27,
    "bytes28": Bytes28,
    "bytes29": Bytes29,
    "bytes30": Bytes30,
    "bytes31": Bytes31,
    "bytes32": Bytes32,

    "bytes": bytes,

    "string": str,

    "address": Address,

    # solidity_parser specific; Did not introduce fixed size yet.
    "ArrayTypeName": typing.List,

    "Mapping": typing.Dict,

})
