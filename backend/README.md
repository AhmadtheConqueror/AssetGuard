# AssetGuard Backend

Apply migrations before starting the API:

```powershell
alembic upgrade head
```

Create the first administrator interactively from the `backend` directory. The password is read without terminal echo and is stored only as an Argon2 hash:

```powershell
python -m scripts.create_admin
```

Authentication uses short-lived stateless bearer tokens. Logout is client-side token disposal in this phase; token revocation and refresh tokens are intentionally not included.

Sensor ingestion currently requires an administrator token. A later machine-ingestion phase should replace that user permission with a scoped device or service credential.
