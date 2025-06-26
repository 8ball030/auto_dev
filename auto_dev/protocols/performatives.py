"""Module for parsing protocol performatives."""

SCALAR_MAP = {
    "int": "conint(ge=Int32.min(), le=Int32.max())",
    "float": "confloat(ge=Double.min(), le=Double.max())",
    "bool": "bool",
    "str": "str",
    "bytes": "bytes",
}


def _split_top_level(s: str, sep: str = ",") -> list[str]:
    parts = []
    current = []
    depth = 0
    for c in s:
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        parts.append("".join(current).strip())
    return parts


def parse_annotation(annotation: str) -> str:
    """Parse Performative annotation."""

    if annotation.startswith("pt:"):
        core = annotation[3:]
    elif annotation.startswith("ct:"):
        return annotation[3:]
    else:
        msg = f"Unknown annotation prefix in: {annotation}"
        raise ValueError(msg)

    if core.startswith("optional[") and core.endswith("]"):
        inner = core[len("optional[") : -1]
        return f"Optional[{parse_annotation(inner)}]"
    if core.startswith("list[") and core.endswith("]"):
        inner = core[len("list[") : -1]
        return f"tuple[{parse_annotation(inner)}]"  # quirk of the framework!
    if core.startswith("dict[") and core.endswith("]"):
        inner = core[len("dict[") : -1]
        key_str, value_str = _split_top_level(inner)
        return f"dict[{parse_annotation(key_str)}, {parse_annotation(value_str)}]"
    if core.startswith("union[") and core.endswith("]"):
        inner = core[len("union[") : -1]
        parts = _split_top_level(inner)
        return " | ".join(parse_annotation(p) for p in parts)
    return SCALAR_MAP[core]
