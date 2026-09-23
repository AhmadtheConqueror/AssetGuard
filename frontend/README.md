# AssetGuard Frontend

The Next.js frontend provides the role-aware local operator interface. It keeps the backend JWT in a server-managed HttpOnly cookie and proxies authenticated API requests through Next.js route handlers.

See the [project README](../README.md) for local setup, RBAC, workflows, and validation commands. The only required frontend environment setting is the server-side `BACKEND_API_URL`; it must not be exposed as a `NEXT_PUBLIC_*` variable.
