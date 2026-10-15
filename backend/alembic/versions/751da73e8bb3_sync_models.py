"""sync_models

Revision ID: 751da73e8bb3
Revises: 30d74c51b4ff
Create Date: 2026-10-15 01:20:50.773327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '751da73e8bb3'
down_revision: Union[str, None] = '30d74c51b4ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('policy_documents', sa.Column('file_hash', sa.String(length=64), nullable=True))
    op.add_column('policy_documents', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.add_column('policy_documents', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('policy_documents', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.create_index(op.f('ix_policy_documents_content_hash'), 'policy_documents', ['content_hash'], unique=False)
    op.create_index(op.f('ix_policy_documents_file_hash'), 'policy_documents', ['file_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_policy_documents_file_hash'), table_name='policy_documents')
    op.drop_index(op.f('ix_policy_documents_content_hash'), table_name='policy_documents')
    op.drop_column('policy_documents', 'is_active')
    op.drop_column('policy_documents', 'error_message')
    op.drop_column('policy_documents', 'content_hash')
    op.drop_column('policy_documents', 'file_hash')
