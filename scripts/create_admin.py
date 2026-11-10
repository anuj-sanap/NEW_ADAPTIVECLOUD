"""scripts/create_admin.py
Create or update an administrative user for the AdaptiveCloud backend.
Can be executed interactively or with CLI arguments:
    python scripts/create_admin.py --username admin --email admin@adaptivecloud.local --password adminpassword123
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Try loading from repo root .env first, then backend/.env
repo_root = Path(__file__).resolve().parent.parent
if (repo_root / ".env").exists():
    load_dotenv(repo_root / ".env")
elif (backend_dir / ".env").exists():
    load_dotenv(backend_dir / ".env")

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password


async def create_or_update_admin(username: str, email: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User).where((User.username == username) | (User.email == email))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            print(f"User '{username}' already exists. Updating password & role...")
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
        else:
            print(f"Creating new admin user '{username}'...")
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)
        print(f"Admin user configured successfully: {user.username} (ID: {user.id})")


def parse_args():
    parser = argparse.ArgumentParser(description="Create AdaptiveCloud Admin User")
    parser.add_argument("--username", default=os.getenv("DEFAULT_ADMIN_USER", "admin"))
    parser.add_argument("--email", default=os.getenv("DEFAULT_ADMIN_EMAIL", "admin@adaptivecloud.local"))
    parser.add_argument("--password", default=os.getenv("DEFAULT_ADMIN_PASS", "adminpassword123"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(create_or_update_admin(args.username, args.email, args.password))

