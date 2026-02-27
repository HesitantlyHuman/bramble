from typing import List, Callable, Awaitable, Dict, Set, Any, Tuple

import string
import random
import asyncio
import math

import bramble

# TODO: create slow task branches
# TODO: create large text branches
# TODO: create high volume logging branches


def generate_branch_names(num: int, length: int = 30) -> Set[str]:
    names = set()
    for _ in range(num):
        next_name = "".join(random.choices(string.ascii_letters, k=length))
        names.add(next_name)
    return names


def create_children(
    name_bank: Dict[str, Set[str]],
    tag_bank: Dict[str, Set[str]],
    metadata_bank: Dict[str, Dict[str, Any]],
    current_depth: int,
    max_depth: int,
    max_branch: int,
    target_branching: int,
    weights: Dict[str, float],
) -> List[List[Any]]:
    # Now we need to create the children
    mu = (math.log(max(target_branching * 0.9, 1))) ** (1 / 2) + 1
    num_children = int(random.lognormvariate(mu=mu, sigma=1))
    num_children = max(0, min(num_children, max_branch))

    if num_children == 0:
        return []

    # Create groups
    group_sizes = []
    total = 0
    while total < num_children:
        next_group = int(
            random.lognormvariate(
                mu=(math.log(max(target_branching / 2.25, 1))) ** (1 / 2) + 1,
                sigma=1,
            )
        )
        next_group = max(1, min(next_group, max_branch))
        if total + next_group > num_children:
            next_group = num_children - total
        group_sizes.append(next_group)
        total += next_group

    dispatch_types = list(weights.keys())
    dispatch_weights = [weights[t] for t in dispatch_types]
    dispatch_weights_sum = sum(dispatch_weights)
    dispatch_weights = [w / dispatch_weights_sum for w in dispatch_weights]

    groups = []
    for group_size in group_sizes:
        group = []
        for _ in range(group_size):
            dispatch_type = random.choices(dispatch_types, dispatch_weights, k=1)[0]
            group.append(
                create_log_config(
                    dispatch_type=dispatch_type,
                    name_bank=name_bank,
                    tag_bank=tag_bank,
                    metadata_bank=metadata_bank,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    max_branch=max_branch,
                    target_branching=target_branching,
                    weights=weights,
                )
            )
        groups.append(group)
    return groups


def create_log_config(
    dispatch_type: str,
    name_bank: Dict[str, Set[str]],
    tag_bank: Dict[str, Set[str]],
    metadata_bank: Dict[str, Dict[str, Any]],
    current_depth: int,
    max_depth: int,
    max_branch: int,
    target_branching: int,
    weights: Dict[str, float],
) -> Tuple[str, str, Set[str], Dict[str, Any], List[List[Any]]]:
    # Generate branch info
    name = random.choice(name_bank[dispatch_type])
    num_tags = random.randint(0, 4)
    tags = set()
    for _ in range(num_tags):
        tags.update(random.choice(tag_bank[dispatch_type]))
    num_metadata = random.randint(0, 3)
    metadata_keys = set(metadata_bank[dispatch_type].keys())
    metadata = {}
    for _ in range(num_metadata):
        key = random.choice(metadata_keys)
        metadata[key] = metadata_bank[dispatch_type][key]

    if current_depth == max_depth:
        return (dispatch_type, name, tags, metadata, [])

    return (
        dispatch_type,
        name,
        tags,
        metadata,
        create_children(
            name_bank=name_bank,
            tag_bank=tag_bank,
            metadata_bank=metadata_bank,
            current_depth=current_depth,
            max_depth=max_depth,
            max_branch=max_branch,
            target_branching=target_branching,
            weights=weights,
        ),
    )


async def run_simple(
    name: str, tags: Set[str], metadata: Dict[str, Any], children: List[List[Any]]
):
    # First, the simple forking
    with bramble.fork(name=name, tags=tags, metadata=metadata):
        # Now, we need to run the next calls
        for group_num, group in enumerate(children):
            bramble.log(f"Now collecting group: {group_num}")  # The simple log
            to_run = []
            for child in group:
                child_type, child_name, child_tags, child_metadata, child_children = (
                    child
                )
                dispatch_function = DISPATCH_FUNCTIONS[child_type]
                to_run.append(
                    dispatch_function(
                        child_name, child_tags, child_metadata, child_children
                    )
                )
            await asyncio.gather(*to_run)


DISPATCH_FUNCTIONS: Dict[str, Callable[[], Awaitable]] = {"simple": run_simple}


# TODO: this should take a writer object, so that we can test with different
# writer configurations.
def run_test(
    max_depth: int = 10,
    max_branch: int = 20,
    avg_branch: int = 3,
    weights: Dict[str, float] = {"simple": 1.0},
    num_trials: int = 3,
):
    # Create banks
    name_bank = {}
    tag_bank = {}
    metadata_bank = {}

    # Now, sample for a top level node
    dispatch_types = list(weights.keys())
    dispatch_weights = [weights[t] for t in dispatch_types]
    dispatch_weights_sum = sum(dispatch_weights)
    dispatch_weights = [w / dispatch_weights_sum for w in dispatch_weights]
    dispatch_type = random.choices(dispatch_types, dispatch_weights, k=1)[0]

    # Create the test
    test = create_log_config(
        dispatch_type=dispatch_type,
        name_bank=name_bank,
        tag_bank=tag_bank,
        metadata_bank=metadata_bank,
        current_depth=0,
        max_depth=max_depth,
        target_branching=avg_branch,
        max_branch=max_branch,
        weights=weights,
    )

    # Now, we need to run the test num_trials times without logging to get the
    # base speed

    # Then run the test num_trials times to get the speed with logging enabled
    # (no backend, just compression into memory storage)

    # Now, compare the average times, and the average data storage size to
    # report the test results


if __name__ == "__main__":
    print(create_children(0, 10, 20, 3, {}))
