"""
Compare the ABIs and source code of two smart contracts
"""

import difflib
import operator
from dataclasses import asdict
from itertools import zip_longest
from typing import Any, Dict, Union, cast

from .polygon_api import PolygonAPI
from .utils import get_logger

logger = get_logger()


def are_all_instances_of(*args: object, type: Union[type, tuple[type, ...]]) -> bool:  # noqa
    """Check all instances are of type `type`."""

    return all(isinstance(arg, type) for arg in args)


def data_diff(d1: Union[list, dict], d2: Union[list, dict]) -> dict:  # noqa
    """Compare containers for differences."""

    diff: Dict[str, Any] = {}

    # dictionary keys are sorted by order of insertion since python3.7
    if are_all_instances_of(d1, d2, type=list):  # integer keys
        d1, d2 = dict(enumerate(d1)), dict(enumerate(d2))

    d1, d2 = cast(dict, d1), cast(dict, d2)
    for k in d1.keys() | d2.keys():
        v1, v2 = d1.get(k), d2.get(k)  # noqa
        if isinstance(v1, dict) and isinstance(v2, dict):
            if nested_diff := data_diff(v1, v2):
                diff[k] = nested_diff
        elif v1 != v2:
            diff[k] = (v1, v2)

    return diff


def print_diff_details(diff: dict) -> None:  # type: ignore
    """Print details of the differences."""

    def print_diff_list(*values: list):
        for idx, (left, right) in enumerate(zip_longest(*values, fillvalue=[])):  # noqa
            if are_all_instances_of(left, right, type=(dict, list)):
                if diff := data_diff(left, right):
                    logger.info(f"Index {idx}:")
                    print_diff_details(diff)
            elif left != right:
                logger.info(f"Index {idx}: {left} != {right}")

    for key, value in diff.items():
        if isinstance(value, dict):
            logger.info(f"{key}:")
            print_diff_details(value)
        elif isinstance(value, tuple):
            logger.info(f"Diff found in {key}:")
            if are_all_instances_of(*value, type=list):
                print_diff_list(*value)
            elif are_all_instances_of(*value, type=dict):
                print_diff_details(data_diff(*value))
            elif operator.ne(*value):
                if are_all_instances_of(*value, type=str):
                    left_lines, right_lines = map(str.splitlines, value)
                    line_diff = difflib.unified_diff(left_lines, right_lines)
                    logger.info("\n".join(line_diff))
                else:
                    logger.info(" != ".join(*value))


def compare_contracts(contract_a: str, contract_b: str, verbose: bool = False) -> None:
    """Compare smart contracts using the Polygon API."""

    api = PolygonAPI()

    addresses = contract_a, contract_b
    abis = api.contract.get_abi(*addresses)
    if diff := data_diff(*map(asdict, abis)):
        logger.warning("Differences in ABIs found")
        if verbose:
            print_diff_details(diff)

    source_codes = api.contract.get_source_code(*addresses)
    if diff := data_diff(*map(asdict, source_codes)):
        logger.warning("Differences in SourceCode found")
        logger.info(f"--- {contract_b}")
        logger.info(f"+++ {contract_a}")
        if verbose:
            print_diff_details(diff)
