"""
Cleanup script to purge all dummy cases, documents, extracted data,
findings, review decisions, and audit entries from the database.
"""
import asyncio
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_all")

async def purge_all_data():
    async with engine.begin() as conn:
        logger.info("Purging all dummy data from tables...")
        
        # Disable triggers or truncate with CASCADE
        # In Postgres, TRUNCATE ... CASCADE is the cleanest and fastest way
        # to wipe tables while honoring/clearing all FK relationships.
        tables = [
            "compliance_findings",
            "review_decisions",
            "audit_entries",
            "extracted_data",
            "procurement_cases",
            "documents",
            "policy_chunks",
            "compliance_rules",
            "policy_documents",
        ]
        
        for table in tables:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                logger.info(f"Truncated table {table}")
            except Exception as e:
                logger.warning(f"Failed to truncate {table}: {e}")

        logger.info("All data purged successfully.")

if __name__ == "__main__":
    asyncio.run(purge_all_data())
