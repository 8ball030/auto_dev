"""Protocol scaffolder."""

import re
import ast
import datetime
import tempfile
import textwrap
import subprocess
from typing import Any
from pathlib import Path
from itertools import starmap
from collections import namedtuple

import yaml
from jinja2 import Environment, FileSystemLoader
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.fmt import Formatter
from auto_dev.enums import BehaviourTypes
from auto_dev.utils import currenttz, get_logger, remove_prefix, camel_to_snake, snake_to_camel
from auto_dev.fsm.fsm import FsmSpec
from auto_dev.constants import DEFAULT_TZ, DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.exceptions import UserInputError
from auto_dev.protocols.scaffolder import PROTOBUF_TO_PYTHON, ProtocolScaffolder, read_protocol, parse_protobuf_type
from auto_dev.data.connections.template import HEADER


ProtocolSpecification = namedtuple("ProtocolSpecification", ["metadata", "custom_types", "speech_acts"])


README_TEMPLATE = """
# {name} Protocol

## Description

...

## Specification

```yaml
{protocol_definition}
```
"""

DEFAULT_TARGET_CONNECTION = "eightballer/docker_engine:0.1.0"


DEFAULT_TYPE_MAP = {
    "str": "'string-type'",
    "int": 8,
    "float": 8.8,
    "bool": False,
    "Dict": {},
    "List": [],
    "Optional": None,
    "Tuple": (),
}

# We now genertae the List[TYPE] and Dict[TYPE, TYPE] types
for _type in DEFAULT_TYPE_MAP.copy():
    if _type != "Optional":
        DEFAULT_TYPE_MAP[f"List[{_type}]"] = []
        DEFAULT_TYPE_MAP[f"Dict[{_type}, {_type}]"] = {}


PYTHHON_KEYWORDS = [
    "None",
    "False",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "also",
    "all",
    "await",
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
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
    "print",
    "abs",
    "delattr",
    "hash",
    "memoryview",
    "set",
    "all",
    "dict",
    "max",
]


class BehaviourScaffolder(ProtocolScaffolder):
    """ProtocolScaffolder."""

    component_class: str = "behaviours"
    type: str = None

    def __init__(
        self, protocol_specification_path: str, behaviour_type, logger, verbose: bool = True, auto_confirm: bool = False
    ):
        """Initialize ProtocolScaffolder."""
        self.logger = logger or get_logger()
        self.verbose = verbose
        self.behaviour_type = behaviour_type
        self.protocol_specification_path = protocol_specification_path
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")
        self.auto_confirm = auto_confirm
        self.env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    @property
    def scaffold(self):
        """Scaffold the protocol."""
        return (
            self._scaffold_simple_fsm if self.behaviour_type is BehaviourTypes.simple_fsm else self._scaffold_protocol
        )

    @property
    def template(self) -> Any:
        """Get the template."""
        return self.env.get_template(str(Path(self.component_class) / f"{self.behaviour_type.value}.jinja"))

    def _validate_selection(self, target_speech_acts, speech_acts):
        if not target_speech_acts:
            target_speech_acts = speech_acts.keys()
        else:
            target_speech_acts = target_speech_acts.split(",")
            failures = []
            for target in target_speech_acts:
                if target not in speech_acts:
                    failures.append(target)
            if failures:
                raise UserInputError(
                    textwrap.dedent(f"""
                    Speech act {target} not found in the protocol specification. 
                    Available: {list(speech_acts.keys())}
                    """)
                )
        return target_speech_acts

    def _scaffold_simple_fsm(
        self,
        target_speech_acts=None,
    ) -> None:
        """Scaffold the simple fsm behaviour from a fsm class."""
        del target_speech_acts

        fsm_spec = FsmSpec.from_yaml(Path(self.protocol_specification_path).read_text())

        all_states = fsm_spec.states
        states_not_in_initial_or_final = [
            state for state in all_states if state not in fsm_spec.final_states + [fsm_spec.default_start_state]
        ]

        transitions: list = []

        for key, destination in fsm_spec.transition_func.items():
            source, event = key[1:-1].split(", ")
            transitions.append({"source": source, "event": event, "destination": destination})

        output = self.template.render(
            fsm_spec=fsm_spec,
            class_name=snake_to_camel(fsm_spec.label).capitalize(),
            states=fsm_spec.states,
            default_start_state=fsm_spec.default_start_state,
            final_states=fsm_spec.final_states,
            events=fsm_spec.alphabet_in,
            remaining_states=states_not_in_initial_or_final,
            transitions=transitions,
        )
        print(output)

    def _scaffold_protocol(self, target_speech_acts=None) -> None:
        """Scaffold the protocol."""
        protocol_specification = read_protocol(self.protocol_specification_path)
        raw_classes, all_dummy_data, enums = self._get_definition_of_custom_types(protocol=protocol_specification)

        speech_acts = protocol_specification.metadata["speech_acts"]

        type_map = {}
        for _type in protocol_specification.custom_types:
            type_map[_type] = _type[3:]
            DEFAULT_TYPE_MAP[_type[3:]] = _type[3:]

        target_speech_acts = self._validate_selection(target_speech_acts, speech_acts)

        parsed_speech_acts = {}
        type_imports = set()

        def recursively_extract_all_imports(
            py_type,
        ):
            if py_type in ["str", "int", "float", "bool"]:
                return
            if py_type.startswith("List"):
                type_imports.add("List")
                recursively_extract_all_imports(py_type[5:-1])
            elif py_type.startswith("Dict"):
                # We split the dict into two parts
                type_imports.add("Dict")
                key, value = py_type[5:-1].split(", ")
                recursively_extract_all_imports(key)
                recursively_extract_all_imports(value)
            elif py_type.startswith("Optional"):
                type_imports.add("Optional")
                recursively_extract_all_imports(py_type[9:-1])

        for speech_act, data in speech_acts.items():
            if speech_act not in target_speech_acts:
                continue
            default_kwargs = {}
            for arg, arg_type in data.items():
                py_arg, py_type = get_py_type_and_args(arg, arg_type, type_map)

                recursively_extract_all_imports(py_type)

                default_kwargs[arg] = (py_type, DEFAULT_TYPE_MAP[py_type], py_arg)
            parsed_speech_acts[speech_act] = default_kwargs

        output = self.template.render(
            protocol_name=protocol_specification.metadata["name"],
            author=protocol_specification.metadata["author"],
            year=datetime.datetime.now(currenttz()).year,
            raw_classes=raw_classes,
            all_dummy_data=all_dummy_data,
            enums=enums,
            class_name=snake_to_camel(protocol_specification.metadata["name"]),
            speech_acts=parsed_speech_acts,
            target_connection=DEFAULT_TARGET_CONNECTION,
            type_imports=type_imports,
            roles=protocol_specification.speech_acts["roles"],
        )
        if self.verbose:
            self.logger.info(f"Generated output: {output}")

        print(output)

    def get_data_types(self, protocol_specification: ProtocolSpecification) -> str:
        """Get the data types."""
        data_types = protocol_specification.custom_types
        return data_types


def get_py_type_and_args(arg, arg_type, type_map):
    """
    Get the python type and arguments from a protobuf type.
    """
    if arg in PYTHHON_KEYWORDS:
        py_arg = f"{arg}_"
    else:
        py_arg = arg
    py_type = (
        arg_type.replace("pt:str", "str")
        .replace("pt:int", "int")
        .replace("pt:float", "float")
        .replace("pt:bool", "bool")
    )
    py_type = (
        py_type.replace("pt:dict", "Dict")
        .replace("pt:list", "List")
        .replace("pt:optional", "Optional")
        .replace("pt:tuple", "Tuple")
    )
    for ct, pt in type_map.items():
        py_type = py_type.replace(ct, pt)
    if py_type not in DEFAULT_TYPE_MAP:
        if py_type.startswith("Optional"):
            DEFAULT_TYPE_MAP[py_type] = None
        elif py_type.startswith("Dict"):
            DEFAULT_TYPE_MAP[py_type] = {}
        else:
            raise ValueError(f"Type {py_type} not found in the default type map.")

    return py_arg, py_type
