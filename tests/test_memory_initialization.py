"""Memory import must not allocate models or open vector databases."""
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('name,klass', [('short_term', 'ShortTermMemory'), ('episodic', 'EpisodicMemory'), ('long_term', 'LongTermMemory')])
def test_memory_constructed_only_on_first_request(monkeypatch, name, klass):
    module = importlib.import_module('src.shared.memory.' + name)
    variable = name + '_memory'
    monkeypatch.setattr(module, variable, None)
    instance = SimpleNamespace(user_id='default_user')
    factory = Mock(return_value=instance)
    monkeypatch.setattr(module, klass, factory)
    getter = getattr(module, 'get_' + variable)
    assert getter() is instance
    assert getter() is instance
    factory.assert_called_once()


def test_import_memory_does_not_create_instances():
    # Reload only the defining modules, without constructing any model.
    for name in ('short_term', 'episodic', 'long_term'):
        module = importlib.import_module('src.shared.memory.' + name)
        module = importlib.reload(module)
        assert getattr(module, name + '_memory') is None