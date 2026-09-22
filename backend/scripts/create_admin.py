"""Create an initial administrator with: python -m scripts.create_admin"""

from getpass import getpass

from app.db.session import SessionLocal
from app.schemas.user import UserCreate
from app.services import user_service


def main() -> None:
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        user_data = UserCreate(email=email, full_name=full_name, password=password, role="admin")
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    with SessionLocal() as db:
        if user_service.get_user_by_email(db, user_data.email) is not None:
            raise SystemExit("A user with that email already exists.")
        try:
            user_service.create_user(db, user_data)
        except user_service.DuplicateUserEmailError as exc:
            raise SystemExit("A user with that email already exists.") from exc
    print(f"Administrator created for {user_data.email}.")


if __name__ == "__main__":
    main()
