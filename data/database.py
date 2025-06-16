"""
NOVA ViA Database Configuration and Setup
Database connection, migrations, and utilities
"""

import asyncio
import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
import redis
from pathlib import Path

from config.settings import get_settings
from .models import Base


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Async engine for main database
        self.async_engine = create_async_engine(
            self.settings.database.url.replace('postgresql://', 'postgresql+asyncpg://'),
            pool_size=self.settings.database.pool_size,
            max_overflow=self.settings.database.max_overflow,
            echo=self.settings.database.echo,
            pool_pre_ping=True
        )
        
        # Sync engine for migrations and admin tasks
        self.sync_engine = create_engine(
            self.settings.database.url,
            pool_size=self.settings.database.pool_size,
            max_overflow=self.settings.database.max_overflow,
            echo=self.settings.database.echo,
            pool_pre_ping=True
        )
        
        # TimescaleDB engine for time-series data
        self.timescale_engine = create_async_engine(
            self.settings.database.timescaledb_url.replace('postgresql://', 'postgresql+asyncpg://'),
            pool_size=10,
            max_overflow=5,
            echo=self.settings.database.echo,
            pool_pre_ping=True
        )
        
        # Session factories
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False
        )
        
        # Redis connection
        self.redis_client = None
    
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Test database connection
            async with self.async_engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            # Initialize Redis
            self.redis_client = redis.Redis.from_url(
                self.settings.redis.url,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                decode_responses=True
            )
            
            # Test Redis connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.ping
            )
            
            self.logger.info("Database connections initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @contextmanager
    def get_sync_session(self) -> Generator[Session, None, None]:
        """Get sync database session"""
        with self.sync_session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.sync_engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.sync_engine)
            self.logger.info("Database tables dropped")
        except Exception as e:
            self.logger.error(f"Failed to drop tables: {e}")
            raise
    
    async def setup_timescaledb(self):
        """Setup TimescaleDB hypertables for time-series data"""
        try:
            async with self.timescale_engine.begin() as conn:
                # Create TimescaleDB extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
                
                # Create hypertables for time-series data
                hypertables = [
                    ("eeg_features", "timestamp"),
                    ("neuroplasticity_predictions", "prediction_time"),
                    ("system_metrics", "timestamp"),
                    ("lab_results", "collection_time"),
                    ("medication_administrations", "administered_time"),
                ]
                
                for table, time_column in hypertables:
                    await conn.execute(f"""
                        SELECT create_hypertable('{table}', '{time_column}',
                        if_not_exists => TRUE);
                    """)
                
                self.logger.info("TimescaleDB hypertables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to setup TimescaleDB: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        try:
            await self.async_engine.dispose()
            await self.timescale_engine.dispose()
            self.sync_engine.dispose()
            
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.close
                )
            
            self.logger.info("Database connections closed")
            
        except Exception as e:
            self.logger.error(f"Error during database cleanup: {e}")


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with db_manager.get_async_session() as session:
        yield session


async def get_redis_client():
    """Get Redis client"""
    return db_manager.redis_client


class DatabaseMigration:
    """Database migration utilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def create_migration_table(self):
        """Create migration tracking table"""
        with self.db_manager.get_sync_session() as session:
            session.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    description TEXT
                );
            """)
            session.commit()
    
    def apply_migration(self, version: str, description: str, sql: str):
        """Apply a database migration"""
        try:
            with self.db_manager.get_sync_session() as session:
                # Check if migration already applied
                result = session.execute(
                    "SELECT version FROM schema_migrations WHERE version = %s",
                    (version,)
                ).fetchone()
                
                if result:
                    self.logger.info(f"Migration {version} already applied")
                    return
                
                # Apply migration
                session.execute(sql)
                
                # Record migration
                session.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)",
                    (version, description)
                )
                
                session.commit()
                self.logger.info(f"Migration {version} applied successfully: {description}")
                
        except Exception as e:
            self.logger.error(f"Failed to apply migration {version}: {e}")
            raise
    
    def get_applied_migrations(self) -> list:
        """Get list of applied migrations"""
        with self.db_manager.get_sync_session() as session:
            result = session.execute(
                "SELECT version, description, applied_at FROM schema_migrations ORDER BY applied_at"
            ).fetchall()
            return result
    
    def run_initial_migrations(self):
        """Run initial database migrations"""
        self.create_migration_table()
        
        # Migration 001: Initial schema
        self.apply_migration(
            "001_initial_schema",
            "Create initial database schema",
            "-- Initial schema already created by SQLAlchemy"
        )
        
        # Migration 002: Add indexes for performance
        self.apply_migration(
            "002_performance_indexes",
            "Add performance indexes",
            """
            CREATE INDEX IF NOT EXISTS idx_patient_mrn ON patients(medical_record_number);
            CREATE INDEX IF NOT EXISTS idx_patient_status ON patients(status);
            CREATE INDEX IF NOT EXISTS idx_eeg_device_status ON eeg_devices(status);
            CREATE INDEX IF NOT EXISTS idx_biohacking_device_status ON biohacking_devices(status);
            CREATE INDEX IF NOT EXISTS idx_treatment_type_time ON treatments(treatment_type, start_time);
            CREATE INDEX IF NOT EXISTS idx_agent_type_status ON ai_agents(agent_type, status);
            """
        )
        
        # Migration 003: Add HIPAA audit triggers
        self.apply_migration(
            "003_hipaa_audit",
            "Add HIPAA audit triggers",
            """
            -- Create audit log table
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                record_id UUID,
                operation VARCHAR(10) NOT NULL,
                old_values JSONB,
                new_values JSONB,
                user_id VARCHAR(255),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                ip_address INET,
                user_agent TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_table_time ON audit_log(table_name, timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_log(record_id);
            """
        )


# Initialize migration manager
migration_manager = DatabaseMigration(db_manager)
