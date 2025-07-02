from typing import Dict, Set

import contextvars

_LIVE_BRANCHES: Dict[str, "LogBranch"] = {}
_CURRENT_BRANCH_IDS: contextvars.ContextVar[Set[str] | None] = contextvars.ContextVar(
    "_CURRENT_BRANCH_IDS", default=set()
)
