import unittest

from svlang.registry import Registry


class TestRegistry(unittest.TestCase):
    """Test the Registry class."""

    def test_register_and_create(self):
        """Registered classes should be creatable by key."""
        registry = Registry("test")

        @registry.register("foo")
        class Foo:
            pass

        instance = registry.create("foo")
        self.assertIsInstance(instance, Foo)

    def test_register_with_kwargs(self):
        """Create should pass kwargs to constructor."""
        registry = Registry("test")

        @registry.register("bar")
        class Bar:
            def __init__(self, value):
                self.value = value

        instance = registry.create("bar", value=42)
        self.assertEqual(instance.value, 42)

    def test_keys_returns_registered_keys(self):
        """keys() should return all registered keys."""
        registry = Registry("test")

        @registry.register("a")
        class A:
            pass

        @registry.register("b")
        class B:
            pass

        keys = registry.keys()
        self.assertIn("a", keys)
        self.assertIn("b", keys)
        self.assertEqual(len(keys), 2)

    def test_unknown_key_raises_keyerror(self):
        """Creating with unknown key should raise KeyError."""
        registry = Registry("test")

        with self.assertRaises(KeyError) as ctx:
            registry.create("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    def test_duplicate_key_raises_valueerror(self):
        """Registering duplicate key should raise ValueError."""
        registry = Registry("test")

        @registry.register("dup")
        class First:
            pass

        with self.assertRaises(ValueError) as ctx:
            @registry.register("dup")
            class Second:
                pass

        self.assertIn("dup", str(ctx.exception))
        self.assertIn("already registered", str(ctx.exception))

    def test_contains(self):
        """Registry should support 'in' operator."""
        registry = Registry("test")

        @registry.register("exists")
        class Exists:
            pass

        self.assertIn("exists", registry)
        self.assertNotIn("missing", registry)

    def test_len(self):
        """Registry should support len()."""
        registry = Registry("test")
        self.assertEqual(len(registry), 0)

        @registry.register("one")
        class One:
            pass

        self.assertEqual(len(registry), 1)


class TestStrategyRegistry(unittest.TestCase):
    """Test that strategy_registry is properly configured."""

    def test_strategy_registry_has_lrm(self):
        """strategy_registry should have 'lrm' registered."""
        from svlang.strategy import strategy_registry
        self.assertIn("lrm", strategy_registry)

    def test_strategy_registry_has_genesis2(self):
        """strategy_registry should have 'genesis2' registered."""
        from svlang.strategy import strategy_registry
        self.assertIn("genesis2", strategy_registry)


class TestRendererRegistry(unittest.TestCase):
    """Test that renderer_registry is properly configured."""

    def test_renderer_registry_has_markdown(self):
        """renderer_registry should have 'markdown' registered."""
        from svlang.renderers import renderer_registry
        self.assertIn("markdown", renderer_registry)

    def test_renderer_registry_has_csv(self):
        """renderer_registry should have 'csv' registered."""
        from svlang.renderers import renderer_registry
        self.assertIn("csv", renderer_registry)


if __name__ == '__main__':
    unittest.main()
