"""Base renderer class and registry.

This module defines the abstract TableRenderer interface and the
renderer_registry for plugin-style registration of concrete
implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ..model import Parameter, Port
from ..registry import Registry

# Registry for renderer implementations
renderer_registry = Registry("renderer")


class TableRenderer(ABC):
    """Abstract base class for rendering tables of parameters and ports."""

    @abstractmethod
    def render_signal_table(self, signals: Iterable[Port]) -> str:
        """Render a table of port signals.

        Args:
            signals: Iterable of :class:`Port` objects.

        Returns:
            A string containing the formatted table.
        """
        raise NotImplementedError

    @abstractmethod
    def render_parameter_table(self, params: Iterable[Parameter]) -> str:
        """Render a table of module parameters.

        Args:
            params: Iterable of :class:`Parameter` objects.

        Returns:
            A string containing the formatted table.
        """
        raise NotImplementedError
