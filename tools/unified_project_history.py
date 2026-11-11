"""In-memory undo/redo for validated unified projects; no persistence or UI."""
from __future__ import annotations

from copy import deepcopy

from unified_project_edit import _checked


class History:
    """Snapshot history with atomic application and no shared mutable state.

    Edits are functions taking a project and returning a project. Failed edits leave
    history intact; successful edits clear redo, except when the project is unchanged.
    """

    def __init__(self, project, limit=100):
        _checked(project)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        self._project = deepcopy(project)
        self._undo = []
        self._redo = []
        self._limit = limit

    @property
    def project(self):
        return deepcopy(self._project)

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def apply(self, operation, *args, **kwargs):
        result = operation(deepcopy(self._project), *args, **kwargs)
        _checked(result)
        if result == self._project:
            return self.project
        self._undo.append(self._project)
        self._undo = self._undo[-self._limit:]
        self._project = deepcopy(result)
        self._redo.clear()
        return self.project

    def undo(self):
        if not self._undo:
            raise ValueError("No edit to undo")
        self._redo.append(self._project)
        self._project = self._undo.pop()
        return self.project

    def redo(self):
        if not self._redo:
            raise ValueError("No edit to redo")
        self._undo.append(self._project)
        self._project = self._redo.pop()
        return self.project
