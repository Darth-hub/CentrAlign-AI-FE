-- Safe for first initialization and recovery of an existing volume.
-- Read the secret from the container environment, never a command argument.
\getenv kc_password KEYCLOAK_DB_PASSWORD
SELECT 'CREATE ROLE keycloak LOGIN'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'keycloak')
\gexec
SELECT format('ALTER ROLE keycloak PASSWORD %L', :'kc_password')
\gexec
SELECT 'CREATE DATABASE keycloak OWNER keycloak'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'keycloak')
\gexec
