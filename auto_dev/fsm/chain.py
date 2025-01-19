"""Module to allow the chaining of multiple FSMs together."""

from dataclasses import dataclass

from auto_dev.fsm.fsm import FsmSpec
from auto_dev.constants import DEFAULT_ENCODING


abci_paths = [
    "/home/tom/Desktop/Fun/mad_market_maker/tmp/vendor/eightballer/skills/cex_data_retrieval/fsm_specification.yaml",
    "/home/tom/Desktop/Fun/mad_market_maker/tmp/vendor/valory/skills/reset_pause_abci/fsm_specification.yaml",
]


@dataclass
class Chainer:
    """The chainer class allows us to chain together multiple FSMs."""

    fsms: list[FsmSpec]
    chained_fsm: FsmSpec | None = None

    def validate(self) -> None:
        """We validate the FSMs."""

    def chain(self) -> None:
        """We chain the FSMs together."""
        self.validate()
        self.chained_fsm = FsmSpec(
            alphabet_in=[],
            default_start_state=self.fsms[0].default_start_state,
            final_states=[],
            label="ChainedFSM",
            start_states=[],
            states=[],
            transition_func={},
        )
        all_states = []
        all_transitions = []
        for i, fsm in enumerate(self.fsms):
            # we add the states of the current FSM to the chained FSM
            all_states.extend(fsm.states)
            # we add the name of the transitions of the current FSM to the chained FSM
            for transition in fsm.transition_func:
                # we split the transition into the the transition name
                name = transition.split(", ")[1][:-1]
                if name not in all_transitions:
                    all_transitions.append(name)

            for state in fsm.states:
                if state not in self.chained_fsm.states:
                    self.chained_fsm.states.append(state)
            # we add the transitions of the current FSM to the chained FSM
            for transition in fsm.transition_func:
                self.chained_fsm.transition_func[transition] = fsm.transition_func[transition]
            # we add the start states of the current FSM to the chained FSM
            if i == 0:
                self.chained_fsm.start_states = fsm.start_states
            else:
                # we know it was the last FSM
                # we can therefore add the transitions from the final states of the previous
                # # FSM to the start states of the current FSM
                for final_state in self.fsms[i - 1].final_states:
                    for start_state in fsm.start_states:
                        self.chained_fsm.transition_func[f"({final_state}, DONE)"] = start_state

        all_states = list(set(all_states))
        self.chained_fsm.alphabet_in = list(set(all_transitions))


if __name__ == "__main__":
    fsms = []
    for fsm in abci_paths:
        with open(fsm, encoding=DEFAULT_ENCODING) as file_pointer:
            fsm = FsmSpec.from_yaml(file_pointer.read())
            fsms.append(fsm)
    chainer = Chainer(fsms=fsms)
    chainer.chain()
