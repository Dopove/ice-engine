# Files

- [Admin CLI & Tenant Management](admin-cli.md) - ice/admin/cli.py's tenant, API-key, and telemetry management commands, how to invoke them, and why every command that touches the kernel or SecurityManager currently fails against the rest of the tree.
- [Postgres Auto-Provisioning](database-provisioning.md) - ensure_postgres_available in ice/setup_db.py -- how ICE checks for a reachable Postgres and, if missing, lets the developer choose between a Docker container or a native OS-package install before applying the schema.
- [Deployment & Observability Infrastructure](deployment-infrastructure.md) - The Terraform-managed AWS deployment — ECS gateway plus ADOT collector/Loki sidecars, networking, CloudWatch monitoring, S3/Athena telemetry archival, and the Docker image — including several alarm and Athena-schema defects.
- [Gateway CLI: serve, mount, db, self-update](gateway-cli.md) - ice/cli.py, the registered `ice` console script -- its formerly-broken license_cli import (now removed), and its serve/mount/help/db-update/self-update commands.
