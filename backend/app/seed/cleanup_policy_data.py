"""
Cleanup script to purge all policy documents, policy chunks, and compliance rules
from the database, preparing the system for fresh real-document ingestion.
"""
import asyncio
import logging

from sqlalchemy import delete, update, select
from app.database import AsyncSessionLocal
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.compliance_rule import ComplianceRule
from app.models.finding import ComplianceFinding
from app.models.audit import AuditEntry
from app.models.document import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup")


async def purge_all_policy_data():
    async with AsyncSessionLocal() as session:
        logger.info("Starting policy and rule data purge...")

        # 1. Nullify rule_id and document_id references in findings and audit entries
        await session.execute(
            update(ComplianceFinding).values(rule_id=None)
        )
        await session.execute(
            update(AuditEntry).values(rule_id=None, document_id=None)
        )
        logger.info("Disassociated rule_id and document_id from findings and audit entries.")

        # 2. Delete all compliance rules
        deleted_rules = await session.execute(delete(ComplianceRule))
        logger.info("Deleted %s compliance rules.", deleted_rules.rowcount)

        # 3. Delete all policy chunks
        deleted_chunks = await session.execute(delete(PolicyChunk))
        logger.info("Deleted %s policy chunks.", deleted_chunks.rowcount)

        # 4. Find document IDs linked to policies
        policy_docs = (await session.execute(select(PolicyDocument))).scalars().all()
        policy_doc_file_ids = [p.source_file_id for p in policy_docs if p.source_file_id]

        # 5. Delete all policy documents
        deleted_pols = await session.execute(delete(PolicyDocument))
        logger.info("Deleted %s policy documents.", deleted_pols.rowcount)

        # 6. Delete document records for policy uploads
        if policy_doc_file_ids:
            await session.execute(
                delete(Document).where(Document.id.in_(policy_doc_file_ids))
            )
        await session.execute(
            delete(Document).where(Document.document_type == "POLICY")
        )
        logger.info("Cleaned up policy document file records.")

        await session.commit()
        logger.info("Policy data purge completed successfully!")


if __name__ == "__main__":
    asyncio.run(purge_all_policy_data())
