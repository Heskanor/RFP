"""initial_schema

Revision ID: f617d950135d
Revises: 
Create Date: 2025-08-28 14:46:37.624911

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f617d950135d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable required extensions
    op.execute("create extension if not exists pgcrypto")
    op.execute("create extension if not exists vector")
    
    # Create projects table
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create rfps table
    op.create_table('rfps',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('file_ref', sa.Text(), nullable=True),
        sa.Column('source_type', sa.Text(), nullable=True, server_default=sa.text("'file'")),
        sa.Column('created_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.CheckConstraint("source_type in ('file','text','url')", name='rfps_source_type_check'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create rfp_criteria table
    op.create_table('rfp_criteria',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rfp_id', postgresql.UUID(), nullable=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Numeric(precision=6, scale=3), nullable=True, server_default=sa.text('1.0')),
        sa.Column('ord', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['rfp_id'], ['rfps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rfp_criteria_rfp_id'), 'rfp_criteria', ['rfp_id'], unique=False)
    
    # Create bids table
    op.create_table('bids',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(), nullable=True),
        sa.Column('rfp_id', postgresql.UUID(), nullable=True),
        sa.Column('vendor_name', sa.Text(), nullable=True),
        sa.Column('file_ref', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True, server_default=sa.text("'submitted'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.CheckConstraint("status in ('submitted','withdrawn','scored')", name='bids_status_check'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rfp_id'], ['rfps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bids_project_rfp_status'), 'bids', ['project_id', 'rfp_id', 'status'], unique=False)
    
    # Create bid_responses table
    op.create_table('bid_responses',
        sa.Column('bid_id', postgresql.UUID(), nullable=False),
        sa.Column('criterion_id', postgresql.UUID(), nullable=False),
        sa.Column('extracted_answer', sa.Text(), nullable=True),
        sa.Column('score', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('model_version', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bid_id'], ['bids.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criterion_id'], ['rfp_criteria.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('bid_id', 'criterion_id')
    )
    
    # Create evaluations table
    op.create_table('evaluations',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(), nullable=True),
        sa.Column('rfp_id', postgresql.UUID(), nullable=True),
        sa.Column('method', sa.Text(), nullable=True),
        sa.Column('weights_version', sa.Text(), nullable=True),
        sa.Column('overall_score', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rfp_id'], ['rfps.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create evaluation_breakdown table
    op.create_table('evaluation_breakdown',
        sa.Column('evaluation_id', postgresql.UUID(), nullable=False),
        sa.Column('criterion_id', postgresql.UUID(), nullable=True),
        sa.Column('score', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criterion_id'], ['rfp_criteria.id']),
        sa.PrimaryKeyConstraint('evaluation_id', 'criterion_id')
    )
    
    # Create embeddings table
    op.create_table('embeddings',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(), nullable=True),
        sa.Column('kind', sa.Text(), nullable=True),
        sa.Column('ref_id', postgresql.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # vector(1536) represented as array
        sa.CheckConstraint("kind in ('rfp_criterion','bid_answer')", name='embeddings_kind_check'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embeddings_project_id'), 'embeddings', ['project_id'], unique=False)
    op.create_index(op.f('ix_embeddings_kind'), 'embeddings', ['kind'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_embeddings_kind'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_project_id'), table_name='embeddings')
    op.drop_table('embeddings')
    op.drop_table('evaluation_breakdown')
    op.drop_table('evaluations')
    op.drop_table('bid_responses')
    op.drop_index(op.f('ix_bids_project_rfp_status'), table_name='bids')
    op.drop_table('bids')
    op.drop_index(op.f('ix_rfp_criteria_rfp_id'), table_name='rfp_criteria')
    op.drop_table('rfp_criteria')
    op.drop_table('rfps')
    op.drop_table('projects')

