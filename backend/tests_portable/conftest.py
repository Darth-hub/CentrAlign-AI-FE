import os
import tempfile
from pathlib import Path
import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix='aria-tests-'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(TEST_ROOT / 'test.db')
os.environ['STORAGE_PATH'] = str(TEST_ROOT / 'documents')
os.environ['SERVICE_SECRET'] = 'test-secret-' * 5
os.environ['OIDC_ISSUER'] = 'https://issuer.test/realms/aria'
os.environ['LLM_API_KEY'] = ''

@pytest.fixture(autouse=True)
def clean_database():
    from services.database import engine, metadata, initialize
    initialize()
    with engine.begin() as conn:
        for table in reversed(metadata.sorted_tables): conn.execute(table.delete())
    yield

@pytest.fixture
def claims():
    return {'sub': 'user-1', 'email': 'buyer@example.test', 'p2p_role': 'procurement', 'department': 'Procurement'}
