"""Generic registry for plugin-style class registration.

This module provides a reusable Registry class that enables
decorator-based registration of implementations. This pattern
supports the Open-Closed principle: new implementations can be
added without modifying existing code.

Example usage::

    renderer_registry = Registry("renderer")

    @renderer_registry.register("markdown")
    class MarkdownRenderer(TableRenderer):
        ...

    @renderer_registry.register("csv")
    class CsvRenderer(TableRenderer):
        ...

    # Later, create instance by key
    renderer = renderer_registry.create("csv")
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Type, TypeVar

T = TypeVar("T")


class Registry:
    """A registry for decorator-based class registration.

    Provides a clean way to register and instantiate classes by key,
    eliminating if-else chains and supporting the Open-Closed principle.
    """

    def __init__(self, name: str = "registry") -> None:
        """Initialize the registry.

        Args:
            name: Human-readable name for error messages.
        """
        self._name = name
        self._items: Dict[str, Type[Any]] = {}

    def register(self, key: str) -> Callable[[Type[T]], Type[T]]:
        """Decorator to register a class with the given key.

        Args:
            key: The key to register the class under.

        Returns:
            A decorator that registers the class.

        Raises:
            ValueError: If the key is already registered.
        """
        def decorator(cls: Type[T]) -> Type[T]:
            if key in self._items:
                raise ValueError(
                    f"{self._name}: key '{key}' already registered "
                    f"to {self._items[key].__name__}"
                )
            self._items[key] = cls
            return cls
        return decorator

    def create(self, key: str, **kwargs: Any) -> Any:
        """Create an instance of the registered class.

        Args:
            key: The key of the registered class.
            **kwargs: Arguments to pass to the class constructor.

        Returns:
            An instance of the registered class.

        Raises:
            KeyError: If the key is not registered.
        """
        if key not in self._items:
            available = ", ".join(sorted(self._items.keys()))
            raise KeyError(
                f"{self._name}: unknown key '{key}'. "
                f"Available: {available}"
            )
        return self._items[key](**kwargs)

    def keys(self) -> List[str]:
        """Return a list of registered keys.

        Useful for populating argparse choices dynamically.
        """
        return list(self._items.keys())

    def __contains__(self, key: str) -> bool:
        """Check if a key is registered."""
        return key in self._items

    def __len__(self) -> int:
        """Return the number of registered items."""
        return len(self._items)
