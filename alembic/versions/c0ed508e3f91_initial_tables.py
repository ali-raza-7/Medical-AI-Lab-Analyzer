"""initial tables

Revision ID: c0ed508e3f91
Revises: 
Create Date: 2026-06-15 05:52:44.564727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c0ed508e3f91'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('credits', sa.Integer(), server_default=sa.text('5')),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('failed_login_attempts', sa.Integer(), server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('credit_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('amount', sa.Integer()),
        sa.Column('description', sa.String()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_jti', sa.String(36), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_refresh_tokens_token_jti', 'refresh_tokens', ['token_jti'])

    op.create_table('analyses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('file_name', sa.String(), nullable=True),
        sa.Column('results_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('analyses')
    op.drop_table('refresh_tokens')
    op.drop_table('credit_transactions')
    op.drop_table('users')
