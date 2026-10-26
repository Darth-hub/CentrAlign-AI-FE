"""Existing Keycloak clients must receive the scopes required by API identity."""
import importlib.util
from pathlib import Path
import pytest

@pytest.fixture
def bootstrap_module(monkeypatch):
    for key in ['ERPNEXT_URL', 'KEYCLOAK_URL', 'FRONTEND_ORIGIN']:
        monkeypatch.setenv(key, 'https://example.test')
    monkeypatch.setenv('ERPNEXT_USER_PASSWORD', 'synthetic-test-password')
    source = Path(__file__).resolve().parents[2] / 'scripts/bootstrap.py'
    spec = importlib.util.spec_from_file_location('identity_bootstrap_test', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_existing_client_missing_basic_scope_is_repaired_idempotently(bootstrap_module, monkeypatch):
    assigned = {'email-id', 'roles-id'}
    def keycloak_call(session, method, url, **kwargs):
        if method == 'GET':
            return [{'name': name, 'id': name + '-id'} for name in ['basic', 'email', 'roles']]
        assert method == 'PUT'
        assigned.add(url.rsplit('/', 1)[-1])
    monkeypatch.setattr(bootstrap_module, 'call', keycloak_call)
    for _ in range(2):
        bootstrap_module.ensure_default_scopes(None, 'https://example.test/admin/realms/aria', 'client', ['basic', 'email', 'roles'])
    assert assigned == {'basic-id', 'email-id', 'roles-id'}

def test_missing_required_scope_stops_setup(bootstrap_module, monkeypatch):
    monkeypatch.setattr(bootstrap_module, 'call', lambda *args, **kwargs: [{'name': 'email', 'id': 'email-id'}])
    with pytest.raises(RuntimeError, match='basic'):
        bootstrap_module.ensure_default_scopes(None, 'https://example.test/admin/realms/aria', 'client', ['basic', 'email'])
