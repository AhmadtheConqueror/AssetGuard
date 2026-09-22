from typing import Literal, TypeAlias


UserRole: TypeAlias = Literal["admin", "engineer", "technician", "viewer"]
ALL_ROLES: frozenset[str] = frozenset({"admin", "engineer", "technician", "viewer"})


def is_user_role(value: str) -> bool:
    return value in ALL_ROLES
