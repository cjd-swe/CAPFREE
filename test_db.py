import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.database import AsyncSessionLocal, engine, Base
from backend.app import models
from sqlalchemy import select

async def test_db():
    async with AsyncSessionLocal() as session:
        # Create a capper
        capper = models.Capper(name="Test Capper")
        session.add(capper)
        await session.commit()
        await session.refresh(capper)
        print(f"Created Capper: {capper.name} (ID: {capper.id})")

        # Create a pick
        pick = models.Pick(
            capper_id=capper.id,
            sport="NBA",
            league="NBA",
            match_key="LAL vs BOS",
            pick_text="Lakers -5",
            units_risked=1.0,
            result="PENDING"
        )
        session.add(pick)
        await session.commit()
        await session.refresh(pick)
        print(f"Created Pick: {pick.pick_text} (ID: {pick.id})")

        # Retrieve pick
        result = await session.execute(select(models.Pick).where(models.Pick.id == pick.id))
        retrieved_pick = result.scalars().first()
        print(f"Retrieved Pick: {retrieved_pick.pick_text} from Capper: {retrieved_pick.capper.name}")

if __name__ == "__main__":
    try:
        asyncio.run(test_db())
    except Exception as e:
        print(f"Error: {e}")
