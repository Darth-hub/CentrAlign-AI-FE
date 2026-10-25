"""Generate local secrets without printing them. Existing .env is never overwritten."""
from pathlib import Path
import secrets
root = Path(__file__).resolve().parents[1]
path = root / '.env'
if path.exists(): raise SystemExit('.env already exists; edit it rather than regenerating secrets.')
lines = (root / '.env.example').read_text().splitlines()
text = '\n'.join(line.split('=', 1)[0] + '=' + secrets.token_hex(32) if line.endswith('=generate-me') else line for line in lines)
path.write_text(text + '\n'); path.chmod(0o600)
(root / 'secrets').mkdir(exist_ok=True)
if not (root / 'secrets/erp-users.json').exists():
    (root / 'secrets/erp-users.json').write_text('{}\n')
    (root / 'secrets/erp-users.json').chmod(0o600)
print('Created .env and secrets/erp-users.json. Add your model key locally; do not commit either file.')
