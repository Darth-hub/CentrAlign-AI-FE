"""Configure Keycloak and ERP users; run only after ERP's company setup wizard.

Idempotent setup for the demo tenant. Never prints passwords or API keys.
"""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote
import requests

ROOT = Path(__file__).resolve().parents[1]
ERP = os.environ['ERPNEXT_URL'].rstrip('/')
KC = os.environ['KEYCLOAK_URL'].rstrip('/')
ORIGIN = os.environ['FRONTEND_ORIGIN'].rstrip('/')
PASSWORD = os.environ['ERPNEXT_USER_PASSWORD']

class Session(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', (5, 120))
        return super().request(*args, **kwargs)

def call(session, method, url, **kwargs):
    response = session.request(method, url, **kwargs)
    # Do not include response bodies: providers may reflect credentials.
    if not response.ok:
        raise RuntimeError(f'{method} {url.split("?")[0]} returned HTTP {response.status_code}')
    return response.json() if response.content else None

def wait_ready(url):
    for attempt in range(60):
        try:
            if requests.get(url, timeout=5).ok: return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError('Service did not become ready: ' + url)

def personas():
    source = ast.parse((ROOT / 'utilities/scripts/02_setup_users.py').read_text())
    users = []
    for node in source.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'DEMO_PERSONAS', 'SIMULATION_USERS'} for t in node.targets):
            users.extend(ast.literal_eval(node.value))
    return users

def setup_keycloak(users):
    wait_ready(KC + '/realms/master/.well-known/openid-configuration')
    session = Session()
    token = call(session, 'POST', KC + '/realms/master/protocol/openid-connect/token', data={
        'client_id': 'admin-cli', 'grant_type': 'password', 'username': 'admin',
        'password': os.environ['KEYCLOAK_ADMIN_PASSWORD']})['access_token']
    session.headers['Authorization'] = 'Bearer ' + token
    realm = KC + '/admin/realms/aria'
    response = session.get(realm)
    if response.status_code == 404:
        call(session, 'POST', KC + '/admin/realms', json={
            'realm': 'aria', 'enabled': True, 'registrationAllowed': False,
            'loginWithEmailAllowed': True, 'duplicateEmailsAllowed': False,
            'sslRequired': 'external', 'accessTokenLifespan': 300})
    else: response.raise_for_status()
    roles = {}
    for name in ['requester', 'procurement', 'approver', 'ap_clerk', 'executive', 'admin']:
        response = session.get(realm + '/roles/' + name)
        if response.status_code == 404:
            call(session, 'POST', realm + '/roles', json={'name': name})
        else: response.raise_for_status()
        roles[name] = call(session, 'GET', realm + '/roles/' + name)
    config = {'clientId': 'aria-web', 'name': 'CentrAlign AI workspace', 'protocol': 'openid-connect',
        'enabled': True, 'publicClient': True, 'standardFlowEnabled': True,
        'directAccessGrantsEnabled': False, 'serviceAccountsEnabled': False,
        'redirectUris': [ORIGIN + '/'], 'webOrigins': [ORIGIN],
        'attributes': {'pkce.code.challenge.method': 'S256', 'post.logout.redirect.uris': ORIGIN + '/'},
        'defaultClientScopes': ['web-origins', 'acr', 'profile', 'email', 'roles'],
        'protocolMappers': [
            {'name': 'aria-api-audience', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-audience-mapper',
             'config': {'included.custom.audience': 'aria-api', 'access.token.claim': 'true', 'id.token.claim': 'false'}},
            {'name': 'aria-roles', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-usermodel-realm-role-mapper',
             'config': {'claim.name': 'realm_access.roles', 'jsonType.label': 'String', 'multivalued': 'true',
                 'access.token.claim': 'true', 'id.token.claim': 'true'}},
            {'name': 'department', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-usermodel-attribute-mapper',
             'config': {'user.attribute': 'department', 'claim.name': 'department', 'jsonType.label': 'String',
                 'access.token.claim': 'true', 'id.token.claim': 'true'}}]}
    clients = call(session, 'GET', realm + '/clients', params={'clientId': 'aria-web'})
    if clients:
        # Update origins on redeploy, preserving the client identity.
        call(session, 'PUT', realm + '/clients/' + clients[0]['id'], json=config)
    else: call(session, 'POST', realm + '/clients', json=config)
    for user in users:
        existing = call(session, 'GET', realm + '/users', params={'username': user['email'], 'exact': 'true'})
        if not existing:
            call(session, 'POST', realm + '/users', json={
                'username': user['email'], 'email': user['email'], 'emailVerified': True, 'enabled': True,
                'firstName': user['first_name'], 'lastName': user['last_name'],
                'attributes': {'department': [user['department']]},
                'credentials': [{'type': 'password', 'value': PASSWORD, 'temporary': True}]})
            existing = call(session, 'GET', realm + '/users', params={'username': user['email'], 'exact': 'true'})
        call(session, 'POST', realm + '/users/' + existing[0]['id'] + '/role-mappings/realm',
             json=[roles[user['cognito_role']]])
    print('Keycloak configured: authorization code + PKCE; change the temporary password on first login.')

def setup_erp(users):
    wait_ready(ERP + '/api/method/frappe.ping')
    session = Session()
    call(session, 'POST', ERP + '/api/method/login', data={'usr': 'Administrator', 'pwd': os.environ['ERPNEXT_PASSWORD']})
    company = session.get(ERP + '/api/resource/Company/' + quote('Apex Manufacturing Group', safe=''))
    if company.status_code == 404:
        raise SystemExit('ERP site is ready. Complete its setup wizard at http://localhost:8080 (or SSH tunnel): company Apex Manufacturing Group, abbreviation AMG, currency USD, country United States. Then rerun make bootstrap. See docs/NETLIFY_DEPLOYMENT.md.')
    company.raise_for_status()
    keyfile = Path('/run/secrets/erp-users.json')
    keys = json.loads(keyfile.read_text()) if keyfile.exists() else {}
    for user in users:
        url = ERP + '/api/resource/User/' + quote(user['email'], safe='')
        response = session.get(url)
        if response.status_code == 404:
            call(session, 'POST', ERP + '/api/resource/User', json={
                'email': user['email'], 'first_name': user['first_name'], 'last_name': user['last_name'],
                'enabled': 1, 'new_password': PASSWORD, 'send_welcome_email': 0, 'user_type': 'System User',
                'roles': [{'role': role} for role in user['erpnext_roles']]})
        else: response.raise_for_status()
        if user['email'] not in keys:
            generated = call(session, 'POST', ERP + '/api/method/frappe.core.doctype.user.user.generate_keys', data={'user': user['email']})
            api_key = call(session, 'GET', url)['data']['api_key']
            keys[user['email']] = {'api_key': api_key, 'api_secret': generated['message']['api_secret']}
            # Persist each generated secret immediately; do not rotate working keys on rerun.
            temp = keyfile.with_suffix('.tmp')
            temp.write_text(json.dumps(keys, indent=2)); temp.chmod(0o640); os.chown(temp, 10001, 10001)
            temp.replace(keyfile)
    print('ERP identities and exact-email API credential mapping configured.')
    marker = keyfile.parent / 'seed-complete'
    if not marker.exists():
        subprocess.run([sys.executable, str(ROOT / 'utilities/scripts/04_seed_demo_data.py')], check=True)
        records = call(session, 'GET', ERP + '/api/resource/Material Request', params={'limit_page_length': 1})['data']
        if not records: raise RuntimeError('No demo requisitions were created; inspect seed output before proceeding')
        marker.write_text('Demo seed completed. Delete this marker only to intentionally create another batch.\n')
        marker.chmod(0o600)
    else: print('Demo seed previously completed; preserving existing transactions.')

if __name__ == '__main__':
    users = personas()
    setup_keycloak(users)
    setup_erp(users)
    print('Bootstrap complete. No privileged ERP service account is used by the app.')
