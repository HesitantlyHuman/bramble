from typing import List, Callable, Awaitable, Dict, Set, Any, Tuple

import msgpack
import string
import random
import asyncio
import math
import time

from tqdm import tqdm

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
) -> Tuple[List[List[Any]], int]:
    # Now we need to create the children
    mu = (math.log(max(target_branching * 0.9, 1))) ** (1 / 2) + 1
    num_children = int(random.lognormvariate(mu=mu, sigma=0.5))
    num_children = max(0, min(num_children, max_branch))

    if num_children == 0:
        return [], 0

    # Create groups
    group_sizes = []
    total = 0
    while total < num_children:
        next_group = int(
            random.lognormvariate(
                mu=(math.log(max(target_branching / 2.25, 1))) ** (1 / 2) + 1,
                sigma=0.5,
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
    num_nodes = 0
    for group_size in group_sizes:
        group = []
        for _ in range(group_size):
            dispatch_type = random.choices(dispatch_types, dispatch_weights, k=1)[0]
            child, num_child_nodes = create_log_config(
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
            group.append(child)
            num_nodes += num_child_nodes
        groups.append(group)
    return groups, num_nodes


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
) -> Tuple[Tuple[str, str, Set[str], Dict[str, Any], List[List[Any]]], int]:
    # Generate branch info
    name = random.choice(name_bank[dispatch_type])

    num_tags = random.randint(0, 4)
    tags = set()
    if len(tag_bank[dispatch_type]) > 0:
        for _ in range(num_tags):
            tags.update(random.choice(tag_bank[dispatch_type]))

    num_metadata = random.randint(0, 3)
    metadata_keys = set(metadata_bank[dispatch_type].keys())
    metadata = {}
    if len(metadata_keys) > 0:
        for _ in range(num_metadata):
            key = random.choice(metadata_keys)
            metadata[key] = metadata_bank[dispatch_type][key]

    if current_depth == max_depth:
        return ((dispatch_type, name, tags, metadata, []), 1)

    children, num_nodes = create_children(
        name_bank=name_bank,
        tag_bank=tag_bank,
        metadata_bank=metadata_bank,
        current_depth=current_depth,
        max_depth=max_depth,
        max_branch=max_branch,
        target_branching=target_branching,
        weights=weights,
    )

    return (
        (
            dispatch_type,
            name,
            tags,
            metadata,
            children,
        ),
        num_nodes + 1,
    )


async def run_simple(
    name: str, tags: Set[str], metadata: Dict[str, Any], children: List[List[Any]]
):
    # First, the simple forking
    with bramble.fork(name=name, tags=tags, metadata=metadata):
        # Now, we need to run the next calls
        for group_num, group in enumerate(children):
            bramble.log(
                f"Now collecting group: {group_num}", log_code_location=False
            )  # The simple log
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


def calculate_raw_entry_bytes(entry: bramble.LogEntry) -> int:
    num_bytes = len(entry.message.encode()) + 9
    if entry.entry_metadata:
        num_bytes += len(msgpack.packb(entry.entry_metadata))
    return num_bytes


def calculate_raw_metadata_bytes(
    parent: str | None,
    children: Set[str] | None,
    tags: Set[str] | None,
    metadata: Dict[str, Any] | None,
) -> int:
    num_bytes = 0
    if parent:
        num_bytes += len(parent.encode())

    if children:
        num_bytes += len(msgpack.packb(list(children)))

    if tags:
        num_bytes += len(msgpack.packb(list(tags)))

    if metadata:
        num_bytes += len(msgpack.packb(metadata))

    return num_bytes


def run_test(
    num_simultaneous_chunks: int = 32,
    chunk_size_mb: float = 16.0,
    compression_quality: int = 11,
    max_assignment_imbalance_factor: float = 3.0,
    base_assignment_imbalance_num: int = 10,
    max_depth: int = 6,
    max_branch: int = 10,
    avg_branch: int = 2,
    weights: Dict[str, float] = {"simple": 1.0},
    num_trials: int = 10,
):
    # Create banks
    # TODO: set this up to randomly generate
    name_bank = {"simple": "simple"}
    tag_bank = {"simple": set()}
    metadata_bank = {"simple": {}}

    # Now, sample for a top level node
    dispatch_types = list(weights.keys())
    dispatch_weights = [weights[t] for t in dispatch_types]
    dispatch_weights_sum = sum(dispatch_weights)
    dispatch_weights = [w / dispatch_weights_sum for w in dispatch_weights]
    dispatch_type = random.choices(dispatch_types, dispatch_weights, k=1)[0]

    # Create the test
    # print(f"Building test...")
    test, num_nodes = create_log_config(
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
    # print(f"Built test with {num_nodes} nodes...")
    dispatch_function = DISPATCH_FUNCTIONS[dispatch_type]

    def _get_size(backend: bramble.backends.MemoryBackend) -> int:
        size = 0
        for chunk_data in backend.chunk_data.values():
            size += len(chunk_data)
        return size

    def _get_modified_writer(backend):
        writer = bramble.writer.BrambleWriter(
            backend=backend,
            num_simultaneous_chunks=num_simultaneous_chunks,
            chunk_size_mb=chunk_size_mb,
            compression_quality=compression_quality,
            max_assignment_imbalance_factor=max_assignment_imbalance_factor,
            base_assignment_imbalance_num=base_assignment_imbalance_num,
        )
        old_append_entries = writer.append_entries
        old_update_branch_info = writer.update_branch_info
        writer._written_data_size = 0

        async def _wrap_entries(entries):
            for branch_id, branch_log_entries in entries.items():
                writer._written_data_size += len(branch_id.encode())
                for entry in branch_log_entries:
                    writer._written_data_size += calculate_raw_entry_bytes(entry=entry)

            await old_append_entries(entries)

        async def _wrap_updates(parents, children, tags, metadata):
            if parents is None:
                parents = {}
            if children is None:
                children = {}
            if tags is None:
                tags = {}
            if metadata is None:
                metadata = {}

            branch_ids = (
                set(parents.keys())
                | set(children.keys())
                | set(tags.keys())
                | set(metadata.keys())
            )
            for branch_id in branch_ids:
                writer._written_data_size += len(branch_id.encode())
                writer._written_data_size += calculate_raw_metadata_bytes(
                    parent=parents.get(branch_id),
                    children=children.get(branch_id),
                    tags=tags.get(branch_id),
                    metadata=metadata.get(branch_id),
                )

            await old_update_branch_info(parents, children, tags, metadata)

        writer.append_entries = _wrap_entries
        writer.update_branch_info = _wrap_updates
        return writer

    # Now, we need to run the test num_trials times without logging to get the
    # base speed
    # print(f"Running test without logging...")
    no_bramble_times = []
    for _ in tqdm(
        range(num_trials),
        desc="Non-logging",
        unit="trial",
        postfix={"num_nodes": num_nodes},
        position=1,
        leave=False,
    ):
        _, name, tags, metadata, children = test
        start_time = time.time()
        asyncio.run(dispatch_function(name, tags, metadata, children))
        stop_time = time.time()
        no_bramble_times.append(stop_time - start_time)

    # Then run the test num_trials times to get the speed with logging enabled
    # (no backend, just compression into memory storage)
    # print(f"Running test with logging...")
    stored_data = []
    written_data = []
    bramble_times = []
    for _ in tqdm(
        range(num_trials),
        desc="Logging",
        unit="trial",
        postfix={"num_nodes": num_nodes},
        position=1,
        leave=False,
    ):
        # Create a fresh backend
        logging_backend = bramble.backends.MemoryBackend()
        writer = _get_modified_writer(backend=logging_backend)
        # Start logging
        with bramble.TreeLogger(writer=writer):
            _, name, tags, metadata, children = test
            start_time = time.time()
            asyncio.run(dispatch_function(name, tags, metadata, children))
        stop_time = time.time()

        stored_data.append(_get_size(logging_backend))
        written_data.append(writer._written_data_size)
        bramble_times.append(stop_time - start_time)

    # Now, compare the average times, and the average data storage size to
    # report the test results
    average_bramble_time = sum(bramble_times) / len(bramble_times)
    compression_ratios = [w / s for w, s in zip(written_data, stored_data)]
    average_compression_ratio = sum(compression_ratios) / len(compression_ratios)
    average_non_bramble_time = sum(no_bramble_times) / len(no_bramble_times)
    time_differences = [b - n for b, n in zip(bramble_times, no_bramble_times)]
    average_time_difference = sum(time_differences) / len(time_differences)
    time_ratios = [b - n for b, n in zip(bramble_times, no_bramble_times)]
    average_time_ratio = sum(time_ratios) / len(time_ratios)

    return {
        "with_bramble": average_bramble_time,
        "without_bramble": average_non_bramble_time,
        "compression_ratio": average_compression_ratio,
        "average_time_difference": average_time_difference,
        "average_time_ratio": average_time_ratio,
    }


# TODO: parameterize
def run(num_scenarios: int = 30):
    overall = {
        "with_bramble": [],
        "without_bramble": [],
        "compression_ratio": [],
        "average_time_difference": [],
        "average_time_ratio": [],
    }
    for _ in tqdm(range(num_scenarios), desc="Scenarios", position=0, leave=True):
        overall.update(run_test())

    for key in overall.keys():
        overall[key] = sum(overall[key]) / len(overall[key])

    return overall


if __name__ == "__main__":
    print(run())
