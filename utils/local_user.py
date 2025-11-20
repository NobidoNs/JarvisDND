import os

LOCAL_USER_ID = os.getenv("LOCAL_USER_ID", "local-user")


def get_user_id() -> str:
    """Return a deterministic user id for local, single-user mode."""

    return LOCAL_USER_ID

