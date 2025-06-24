from typing import Self, List

import contextvars
import asyncio
import uuid

from collections import deque


class Node:
    id: str
    parent: str

    def __init__(self, parent: str | None = None):
        self.parent = parent
        self.id = str(uuid.uuid4().hex)[:16]

    def __repr__(self):
        return f"Node(parent='{self.parent}')"


# The tree is the same between all running "threads"
# The only thing that is different is the current node
# So we should hold the tree in a normal global

TREE = {}
CURRENT_NODE = contextvars.ContextVar("CURRENT_NODE", default=None)


def get_current():
    return CURRENT_NODE.get()


def branch(func):
    async def wrapper(*args, **kwargs):
        if TREE is None:
            root = Node()
            TREE[root.id] = root
            CURRENT_NODE.set(root.id)
            return_node = root.id
        else:
            current_node = CURRENT_NODE.get()
            next_node = Node(parent=current_node)
            TREE[next_node.id] = next_node
            CURRENT_NODE.set(next_node.id)
            return_node = next_node.id

        await func(*args, **kwargs)
        CURRENT_NODE.set(return_node)

    return wrapper


@branch
async def function_one():
    print(f"Function one initial: {get_current()}")
    await asyncio.gather(function_two(), function_two())
    print(f"Function one final: {get_current()}")


@branch
async def function_two():
    print(f"Function two initial: {get_current()}")
    await asyncio.sleep(0.5)
    print(f"Function two final: {get_current()}")


async def main():
    await function_one()


asyncio.run(main())


print(TREE)
