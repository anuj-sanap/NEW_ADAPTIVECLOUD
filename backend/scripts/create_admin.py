"""
backend/scripts/create_admin.py
One-time script to create the first admin user.
Run from the backend/ directory with the venv activated:
    python scripts/create_admin.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def create_admin(username: str, email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"✅ Admin user created: {user.username!r} (id={user.id})")


if __name__ == "__main__":
    print("Create Admin User")
    print("-" * 40)
    uname = input("Username: ").strip()
    email = input("Email: ").strip()
    pwd = input("Password: ").strip()
    confirm = input("Confirm password: ").strip()

    if pwd != confirm:
        print("❌ Passwords do not match")
        sys.exit(1)
    if len(pwd) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(create_admin(uname, email, pwd))
