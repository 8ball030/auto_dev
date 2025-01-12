"""Tools to parse fsm specs."""

from string import Template
from pathlib import Path
from collections import Counter
from dataclasses import dataclass

import yaml

from auto_dev.utils import camel_to_snake
from auto_dev.constants import DEFAULT_ENCODING


# we define our base template
BASE_MERMAID_TEMPLATE = Template(
    """
graph TD
  $start_state
  $states
  $transitions
"""
)

# we define the FSM template

SAMPLE_MERMAID = """
graph TD
    A[Christmas] -->|Get money| B(Go shopping)
    B --> C{Let me think}
    C -->|One| D[Laptop]
    C -->|Two| E[iPhone]
    C -->|Three| F[fa:fa-car Car]
"""


STATE_TEMPLATE = Template("""$state""")
TRANSITION_TEMPLATE = Template("""$start_state -->|$transition| $end_state""")


def validate_name(name: str) -> str:
    """Validate an fsm name."""
    if not name:
        raise ValueError("Name must not be empty.")
    if not name.endswith("AbciApp"):
        raise ValueError("Name must end with AbciApp.")
    return name


@dataclass
class FsmSpec:
    """We represent a fsm spec."""

    alphabet_in: list[str]
    default_start_state: str
    final_states: list[str]
    label: str
    start_states: list[str]
    states: list[str]
    transition_func: dict[tuple[str, str], str]

    @classmethod
    def from_yaml(cls, yaml_str: str, label: str = None):
        """We create a FsmSpec from a yaml string."""
        fsm_spec = yaml.safe_load(yaml_str)
        if label:
            fsm_spec["label"] = label
        label = fsm_spec["label"]
        validate_name(label)
        return cls(**fsm_spec)

    @classmethod
    def from_path(cls, path: Path, label: str = None):
        """We create a FsmSpec from a yaml file."""
        with open(path, encoding=DEFAULT_ENCODING) as file_pointer:
            return cls.from_yaml(file_pointer.read(), label)

    @classmethod
    def from_mermaid_path(cls, path: Path, label: str):
        """We create a FsmSpec from a yaml file."""
        validate_name(label)
        with open(path, encoding=DEFAULT_ENCODING) as file_pointer:
            res = cls.from_mermaid(file_pointer.read())
            res.label = label
        return res

    def to_mermaid(self):
        """We convert the FsmSpec to a mermaid string."""
        start_state = STATE_TEMPLATE.substitute(state=self.default_start_state)
        # join on new line
        states = "\n  ".join([STATE_TEMPLATE.substitute(state=state) for state in self.states])
        transitions = []
        for transition, end_state in self.transition_func.items():
            _start_state, _transition = transition[1:-1].split(", ")
            transitions.append(
                TRANSITION_TEMPLATE.substitute(start_state=_start_state, transition=_transition, end_state=end_state)
            )
        # we join on new line
        transitions = "\n  ".join(transitions)

        return BASE_MERMAID_TEMPLATE.substitute(start_state=start_state, states=states, transitions=transitions)

    @classmethod
    def from_mermaid(cls, mermaid_str: str):
        """Parse a mermaid string to a FsmSpec.
        note, we need to create a graph like structure.
        we parse each line and create a node and a edge.
        """
        if mermaid_str.find("graph TD") != -1:
            return cls._handle_graph(mermaid_str)

        if mermaid_str.find("stateDiagram-v2") != -1:
            return cls._handle_state_diagram_v2(mermaid_str)

        msg = "We do not support this mermaid format!"
        raise ValueError(msg)

    @classmethod
    def _handle_graph(cls, graph):  # pylint: disable=R0912  # noqa
        """We handle the graph case."""
        states = []
        transitions = []

        for line in graph.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("graph"):
                continue
            if line.startswith("%%"):
                continue
            items = line.split()
            if len(items) == 1:
                states.append(items[0])
            else:
                if len(items) != 3:
                    msg = f"Invalid line {line}"
                    raise ValueError(msg)
                start_state, _transition, end_state = items

                states.extend((start_state, end_state))
                transition = _transition.split("|")[1]
                transitions.append(((start_state, transition), end_state))
        # we need to create the alphabet_in
        alphabet_in = sorted({transition[1].upper() for transition, _ in transitions})  # pylint: disable=R1718
        # we need to create the transition_func
        transition_func = {}
        for transition, end_state in transitions:
            key = f"({transition[0]}, {transition[1].upper()})"
            transition_func[key] = end_state
        # we need to create the start_states
        # we can do this by using our transition_func to find the start states
        # we traverse the transition_func and find the start states
        start_states = []
        for start_state, _ in transitions:
            if start_state[0] not in transition_func.values():
                start_states.append(start_state)
        # we need to create the final_states
        # we can do this by using our transition_func to find the final states
        # we traverse the transition_func and find the final states
        final_states = []

        def clean(transition):
            return transition.split(", ")[0][1:]

        vals = [clean(i) for i in transition_func]
        for end_state in transition_func.values():
            if end_state not in vals and end_state not in final_states:
                final_states.append(end_state)

        if not start_states:
            # we need to determine the start state by using a counter
            counter = Counter(states)
            start_states = [counter.most_common(1)[0][0]]
        else:
            start_states = list({f[0] for f in start_states})
        initial_state = start_states[0]
        states = list(set(states))

        return cls(
            alphabet_in=list(set(alphabet_in)),
            default_start_state=initial_state,
            final_states=list(set(final_states)),
            label="HelloWorldAbciApp",
            start_states=start_states,
            states=states,
            transition_func=transition_func,
        )

    @classmethod
    def _handle_state_diagram_v2(cls, graph):
        """We handle the state diagram v2 case."""
        states = []
        transitions = []
        initial_states = []
        final_states = []

        for line in graph.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("stateDiagram-v2"):
                continue
            if line.startswith("%%"):
                continue
            items = line.split()
            if len(items) != 4:
                raise ValueError("Incorrect number of items in line!" + line)
            start_state, _, end_state, _transition = items
            transition = camel_to_snake(_transition).upper()
            end_state = end_state[:-1]
            if start_state == "[*]":
                initial_states.append(end_state)
            elif end_state == "[*]":
                final_states.append(start_state)
            else:
                states.extend((start_state, end_state))
                transitions.append(((start_state, transition), end_state))

        # we need to create the alphabet_in
        states = list(set(states))
        alphabet_in = sorted({transition[1] for transition, _ in transitions})  # pylint: disable=R1718
        # we need to create the transition_func
        transition_func = {}
        for transition, end_state in transitions:
            key = f"({transition[0]}, {transition[1]})"
            transition_func[key] = end_state

        # we can do this by using our transition_func to find the start states

        return cls(
            alphabet_in=alphabet_in,
            default_start_state=initial_states[0],
            final_states=final_states,
            label="HelloWorldAbciApp",
            start_states=initial_states,
            states=states,
            transition_func=transition_func,
        )

    def to_string(self):
        """We convert the FsmSpec to a string."""
        return str(
            yaml.safe_dump(self.__dict__),
        )
