

SCALAR_MAP = {
    "int": "Int64",
    "float": "Double",
    "bool": "bool",
    "str": "str",
    "bytes": "bytes",
}


def parse_annotation(annotation: str) -> str:
    """Parse Performative annotation"""

    if annotation.startswith("pt:"):
        core = annotation[3:]
    elif annotation.startswith("ct:"):
        return annotation[3:]
    else:
        raise ValueError(f"Unknown annotation prefix in: {annotation}")

    if core.startswith("optional[") and core.endswith("]"):
        inner = core[len("optional["):-1]
        return f"{parse_annotation(inner)} | None"
    elif core.startswith("list[") and core.endswith("]"):
        inner = core[len("list["):-1]
        return f"list[{parse_annotation(inner)}]"
    elif core.startswith("dict[") and core.endswith("]"):
        inner = core[len("dict["):-1]
        key_str, value_str = (part.strip() for part in inner.split(",", 1))
        return f"dict[{parse_annotation(key_str)}, {parse_annotation(value_str)}]"
    elif core.startswith("union[") and core.endswith("]"):
        inner = core[len("union["):-1]
        parts = (parse_annotation(p.strip()) for p in inner.split(","))
        return " | ".join(parts)
    else:
        return SCALAR_MAP[core]
