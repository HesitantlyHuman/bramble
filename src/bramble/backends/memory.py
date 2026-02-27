# TODO organize imports
from typing import List, Dict, Set

from bramble.backends.base import BrambleBackend


# TODO: type and document
class MemoryBackend(BrambleBackend):
    master_id_list: List[str]
    branch_ids_to_chunks: Dict[str, Dict[str, Set[str]]]
    chunk_data: Dict[str, bytes]
    active_chunks: Set[str]

    def __init__(self):
        self.master_id_list = []
        self.branch_ids_to_chunks = {}
        self.chunk_data = {}
        self.active_chunks = set()

    def append_data(self, chunk_data):
        new_sizes = {}
        for chunk_id, chunk_id_data in chunk_data.items():
            if chunk_id not in self.chunk_data:
                self.chunk_data[chunk_id] = b""
            self.chunk_data[chunk_id] += chunk_id_data
            new_sizes[chunk_id] = len(self.chunk_data[chunk_id])
        return new_sizes

    def assign_chunks(self, branch_chunks, chunk_type):
        for branch_id, chunks_to_assign in branch_chunks.items():
            self.branch_ids_to_chunks.setdefault(chunk_type, {}).setdefault(
                branch_id, set()
            ).update(chunks_to_assign)

    def add_branches(self, branch_ids):
        self.master_id_list.extend(branch_ids)

    def set_active_chunks(self, chunk_ids):
        self.active_chunks = set(chunk_ids)

    def get_branch_ids(self, start=0, stop=None):
        if stop is None:
            stop = -1
        return self.master_id_list[start:stop]

    def get_chunk_ids(self, branch_ids, type):
        output = {}
        for branch_id in branch_ids:
            output[branch_id] = self.branch_ids_to_chunks.setdefault(
                type, {}
            ).setdefault(branch_id, set())
        return output

    def get_data(self, chunk_ids):
        output = {}
        for chunk_id in chunk_ids:
            output[chunk_id] = self.chunk_data[chunk_id]
        return output

    def get_active_chunks(self):
        return self.active_chunks
