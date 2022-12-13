#!/bin/bash

set -e

# https://stackoverflow.com/questions/59895/how-do-i-get-the-directory-where-a-bash-script-is-located-from-within-the-script#59916
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function clean_up_secrets() {
    rm -f "$SCRIPT_DIR/postgres.env" "$SCRIPT_DIR/minio.env" "$SCRIPT_DIR/codeql-snapshot.env"
}

function clean_up() {
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down
    clean_up_secrets
}

trap clean_up SIGINT

clean_up_secrets

minio_root_password=$(openssl rand -hex 32)
postgres_root_password=$(openssl rand -hex 32)

minio_access_key=$(openssl rand -hex 32)
minio_secret_key=$(openssl rand -hex 32)

echo "MINIO_ROOT_USER=minio" > "$SCRIPT_DIR/minio.env"
echo "MINIO_ROOT_PASSWORD=$minio_root_password" >> "$SCRIPT_DIR/minio.env"

echo "POSTGRES_DB=codeql-snapshot" > "$SCRIPT_DIR/postgres.env"
echo "POSTGRES_PASSWORD=$postgres_root_password" >> "$SCRIPT_DIR/postgres.env"


echo "Starting object storage and database"
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --wait

# Unpack the Minio Client
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" exec object-storage gunzip /opt/bin/mc.gz
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" exec object-storage chmod +x /opt/bin/mc
# Add host configuration
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" exec object-storage  /opt/bin/mc config host add codeql-snapshot http://127.0.0.1:9000 minio $minio_root_password
# Add user
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" exec object-storage /opt/bin/mc admin user add codeql-snapshot $minio_access_key $minio_secret_key
# Apply read/write policy to added user
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" exec object-storage /opt/bin/mc admin policy set codeql-snapshot readwrite user=$minio_access_key

echo "export CODEQL_SNAPSHOT_STORAGE_HOST=127.0.0.1:9000" > "$SCRIPT_DIR/codeql-snapshot.env"
echo "export CODEQL_SNAPSHOT_STORAGE_ACCESS_KEY=$minio_access_key" >> "$SCRIPT_DIR/codeql-snapshot.env"
echo "export CODEQL_SNAPSHOT_STORAGE_SECRET_KEY=$minio_secret_key" >> "$SCRIPT_DIR/codeql-snapshot.env"
echo "export CODEQL_SNAPSHOT_CONNECTION_STRING=postgresql://postgres:$postgres_root_password@127.0.0.1/codeql-snapshot" >> "$SCRIPT_DIR/codeql-snapshot.env"
echo "Run source $SCRIPT_DIR/codeql-snapshot.env to setup secrets for codeql-snapshot.py"

read -p "Press any key to shutdown services."

clean_up