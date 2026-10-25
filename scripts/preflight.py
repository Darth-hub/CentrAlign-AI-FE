"""Check local setup without printing credentials or contacting a model provider."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(*args, timeout=10):
    try:
        return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', action='store_true', help='Also probe the Docker engine (10-second timeout).')
    args = parser.parse_args()
    failures = []
    def check(label, ok, next_step=''):
        print(f"{'PASS' if ok else 'TODO'}  {label}" + (f' — {next_step}' if not ok else ''))
        if not ok:
            failures.append(label)

    check('Python 3.13+', sys.version_info >= (3, 13), 'Use Python 3.13 for the project backend.')
    node = run('node', '--version')
    check('Node.js 22+', bool(node and node.returncode == 0 and int(node.stdout.strip().lstrip('v').split('.')[0]) >= 22), 'Install Node.js 22 or newer.')
    check('Docker CLI installed', bool(shutil.which('docker')), 'Install Docker Desktop.')
    env_path = ROOT / '.env'
    check('Private root .env exists', env_path.exists(), 'Run make init once.')
    values = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"\'')
        provider = values.get('LLM_PROVIDER', '')
        check('Model provider selected', provider in {'groq', 'gemini', 'ollama', 'openai-compatible'}, 'Configure LLM_PROVIDER in .env.')
        check('Model ID configured', bool(values.get('LLM_MODEL')), 'Set LLM_MODEL in .env.')
        check('Model key present or local Ollama selected', provider == 'ollama' or bool(values.get('LLM_API_KEY')) and values['LLM_API_KEY'] not in {'YOUR_OWN_KEY', 'YOUR_GROQ_API_KEY', 'your_actual_groq_key'}, 'Add your real provider key locally. This check does not test provider acceptance.')
        names = ['SERVICE_SECRET', 'POSTGRES_PASSWORD', 'KEYCLOAK_DB_PASSWORD', 'MYSQL_ROOT_PASSWORD', 'KEYCLOAK_ADMIN_PASSWORD', 'ERPNEXT_PASSWORD', 'ERPNEXT_USER_PASSWORD']
        check('Generated service secrets present', all(values.get(name) and values[name] != 'generate-me' for name in names), 'Complete make init configuration without overwriting existing credentials.')
        check('Root .env has private permissions', env_path.stat().st_mode & 0o077 == 0, 'Run chmod 600 .env.')
    tracked = run('git', 'ls-files', '--', '.env', 'frontend/.env', 'frontend/.env.local', 'frontend/.env.production', 'secrets')
    check('Private config is not tracked by Git', bool(tracked is not None and tracked.returncode == 0 and not tracked.stdout.strip()), 'Remove private config from Git tracking before pushing.')
    check('Frontend dependencies installed', (ROOT / 'frontend/node_modules').is_dir(), 'Run npm ci --prefix frontend.')
    check('Frontend dependency lockfile exists', (ROOT / 'frontend/package-lock.json').is_file())
    if args.docker:
        engine = run('docker', 'info', '--format', '{{.ServerVersion}}')
        check('Docker engine responding', bool(engine and engine.returncode == 0), 'Open/restart Docker Desktop, then rerun with --docker.')
    else:
        print('SKIP  Docker engine probe (use --docker when ready).')
    print('\nNo credentials were printed. Checks do not prove live model, identity or ERP connectivity.')
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
