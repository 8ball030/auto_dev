"""Module containing custom primitives."""

# ruff: noqa: D101, D102, D105, ARG003, PLW3201

import struct
from abc import ABC, abstractmethod

from pydantic_core import SchemaValidator, core_schema


min_int32 = -1 << 31
max_int32 = (1 << 31) - 1
min_uint32 = 0
max_uint32 = (1 << 32) - 1

min_int64 = -1 << 63
max_int64 = (1 << 63) - 1
min_uint64 = 0
max_uint64 = (1 << 64) - 1

min_float32 = struct.unpack("f", struct.pack("I", 0xFF7FFFFF))[0]
max_float32 = struct.unpack("f", struct.pack("I", 0x7F7FFFFF))[0]
min_float64 = struct.unpack("d", struct.pack("Q", 0xFFEFFFFFFFFFFFFF))[0]
max_float64 = struct.unpack("d", struct.pack("Q", 0x7FEFFFFFFFFFFFFF))[0]


def to_float32(value: float) -> float:
    """Pack the value as a 32-bit float then unpack it."""
    return struct.unpack("f", struct.pack("f", value))[0]


class BaseConstrainedFloat(float, ABC):
    """Base class for constrained float types."""

    @classmethod
    @abstractmethod
    def min(cls) -> float:
        msg = f"{cls.__name__}.min() is not implemented."
        raise NotImplementedError(msg)

    @classmethod
    @abstractmethod
    def max(cls) -> float:
        msg = f"{cls.__name__}.max() is not implemented."
        raise NotImplementedError(msg)

    def __new__(cls, value: float = 0.0, *args, **kwargs) -> "BaseConstrainedInt":
        schema = core_schema.float_schema(strict=True, ge=cls.min(), le=cls.max())
        validator = SchemaValidator(schema)
        validated_value = validator.validate_python(value)
        return super().__new__(cls, validated_value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        schema = core_schema.float_schema(strict=True, ge=cls.min(), le=cls.max())
        return core_schema.no_info_wrap_validator_function(cls, schema)


class BaseConstrainedInt(int, ABC):
    """Base class for constrained integer types."""

    @classmethod
    @abstractmethod
    def min(cls) -> int:
        msg = f"{cls.__name__}.min() is not implemented."
        raise NotImplementedError(msg)

    @classmethod
    @abstractmethod
    def max(cls) -> int:
        msg = f"{cls.__name__}.max() is not implemented."
        raise NotImplementedError(msg)

    def __new__(cls, value: int = 0, *args, **kwargs) -> "BaseConstrainedInt":
        schema = core_schema.int_schema(strict=True, ge=cls.min(), le=cls.max())
        validator = SchemaValidator(schema)
        validated_value = validator.validate_python(value)
        return super().__new__(cls, validated_value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        schema = core_schema.int_schema(strict=True, ge=cls.min(), le=cls.max())
        return core_schema.no_info_wrap_validator_function(cls, schema)


class Double(BaseConstrainedFloat):
    @classmethod
    def min(cls):
        return min_float64

    @classmethod
    def max(cls):
        return max_float64


class Float(BaseConstrainedFloat):
    @classmethod
    def min(cls):
        return min_float32

    @classmethod
    def max(cls):
        return max_float32

    def __new__(cls, value: float = 0.0, *args, **kwargs) -> "Float":
        return super().__new__(cls, to_float32(float(value)))


class Int32(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int32

    @classmethod
    def max(cls):
        return max_int32


class Int64(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int64

    @classmethod
    def max(cls):
        return max_int64


class UInt32(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_uint32

    @classmethod
    def max(cls):
        return max_uint32


class UInt64(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_uint64

    @classmethod
    def max(cls):
        return max_uint64


class SInt32(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int32

    @classmethod
    def max(cls):
        return max_int32


class SInt64(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int64

    @classmethod
    def max(cls):
        return max_int64


class Fixed32(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_uint32

    @classmethod
    def max(cls):
        return max_uint32


class Fixed64(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_uint64

    @classmethod
    def max(cls):
        return max_uint64


class SFixed32(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int32

    @classmethod
    def max(cls):
        return max_int32


class SFixed64(BaseConstrainedInt):
    @classmethod
    def min(cls):
        return min_int64

    @classmethod
    def max(cls):
        return max_int64


FLOAT_PRIMITIVES = {
    "double": "Double",
    "float": "Float",
}

INTEGER_PRIMITIVES = {
    "int32": "Int32",
    "int64": "Int64",
    "uint32": "UInt32",
    "uint64": "UInt64",
    "sint32": "SInt32",
    "sint64": "SInt64",
    "fixed32": "Fixed32",
    "fixed64": "Fixed64",
    "sfixed32": "SFixed32",
    "sfixed64": "SFixed64",
}

PRIMITIVE_TYPE_MAP = {
    "bool": "bool",
    "string": "str",
    "bytes": "bytes",
    **FLOAT_PRIMITIVES,
    **INTEGER_PRIMITIVES,
}
