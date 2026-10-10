#!/bin/bash
# ========================================================
# Python Cloud Studio - Administrative User Management
# Creates or promotes a Super Admin account inside Docker
# ========================================================
set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: ./scripts/create-admin.sh <email> <password> [full_name]"
    echo "Example: ./scripts/create-admin.sh lead_instructor@univ.edu MySecurePass! 'Dr. Jane Smith'"
    exit 1
fi

ADMIN_EMAIL="$1"
ADMIN_PASS="$2"
ADMIN_NAME="${3:-Administrator}"

echo "=========================================================="
echo "Creating / Promoting Super Admin: ${ADMIN_EMAIL}"
echo "=========================================================="

docker compose exec api python -c "
import asyncio
from services.api.database import AsyncSessionLocal
from services.api.models import User
from services.api.auth import hash_password
from sqlalchemy import select
import uuid

async def manage_admin():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.email == '${ADMIN_EMAIL}'))
        user = res.scalar_one_or_none()
        if user:
            user.role = 'super_admin'
            user.can_manage_packages = True
            user.hashed_password = hash_password('${ADMIN_PASS}')
            print('✔ Existing user promoted to super_admin and password updated!')
        else:
            new_user = User(
                id=str(uuid.uuid4()),
                email='${ADMIN_EMAIL}',
                hashed_password=hash_password('${ADMIN_PASS}'),
                full_name='${ADMIN_NAME}',
                role='super_admin',
                is_active=True,
                can_manage_packages=True,
                theme_preference='system'
            )
            session.add(new_user)
            print('✔ New super_admin user created successfully!')
        await session.commit()

asyncio.run(manage_admin())
"

echo "=========================================================="
echo "Done! You can now log in at your Studio URL using ${ADMIN_EMAIL}."
echo "=========================================================="

