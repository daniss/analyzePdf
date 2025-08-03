"""
Backup and disaster recovery management for ComptaFlow
"""
import os
import subprocess
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import logging
from pathlib import Path

from core.config import settings


class BackupManager:
    """Manages database backups and disaster recovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # S3 client for backup storage (if configured)
        self.s3_client = None
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    async def create_database_backup(self, backup_type: str = "scheduled") -> Dict:
        """Create a PostgreSQL database backup"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"comptaflow_backup_{backup_type}_{timestamp}.sql"
            backup_path = f"/tmp/{backup_filename}"
            
            # Parse database URL
            db_url = settings.DATABASE_URL
            # Extract components from DATABASE_URL
            # Format: postgresql+asyncpg://user:pass@host:port/dbname
            url_parts = db_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
            user_pass, host_db = url_parts.split("@")
            user, password = user_pass.split(":")
            host_port, dbname = host_db.split("/")
            host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")
            
            # Create pg_dump command
            pg_dump_cmd = [
                "pg_dump",
                f"--host={host}",
                f"--port={port}",
                f"--username={user}",
                f"--dbname={dbname}",
                "--no-password",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                f"--file={backup_path}"
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            # Execute backup
            self.logger.info(f"Starting database backup: {backup_filename}")
            
            process = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if process.returncode != 0:
                raise Exception(f"pg_dump failed: {process.stderr}")
            
            # Get backup file size
            backup_size = os.path.getsize(backup_path)
            backup_size_mb = backup_size / 1024 / 1024
            
            backup_info = {
                "filename": backup_filename,
                "path": backup_path,
                "size_bytes": backup_size,
                "size_mb": round(backup_size_mb, 2),
                "timestamp": timestamp,
                "type": backup_type,
                "status": "completed"
            }
            
            # Upload to S3 if configured
            if self.s3_client and settings.AWS_BUCKET_NAME:
                s3_key = f"backups/database/{backup_filename}"
                
                self.s3_client.upload_file(
                    backup_path,
                    settings.AWS_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ServerSideEncryption': 'AES256',
                        'Metadata': {
                            'backup_type': backup_type,
                            'timestamp': timestamp,
                            'size_mb': str(backup_size_mb)
                        }
                    }
                )
                
                backup_info["s3_location"] = f"s3://{settings.AWS_BUCKET_NAME}/{s3_key}"
                backup_info["uploaded_to_s3"] = True
                
                # Clean up local file after upload
                os.remove(backup_path)
                backup_info["local_file_cleaned"] = True
            else:
                backup_info["uploaded_to_s3"] = False
                backup_info["note"] = "S3 not configured - backup stored locally"
            
            self.logger.info(f"Database backup completed: {backup_filename} ({backup_size_mb:.2f} MB)")
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def list_backups(self, limit: int = 10) -> List[Dict]:
        """List available backups"""
        backups = []
        
        try:
            if self.s3_client and settings.AWS_BUCKET_NAME:
                # List S3 backups
                response = self.s3_client.list_objects_v2(
                    Bucket=settings.AWS_BUCKET_NAME,
                    Prefix="backups/database/",
                    MaxKeys=limit
                )
                
                for obj in response.get('Contents', []):
                    # Get object metadata
                    head_response = self.s3_client.head_object(
                        Bucket=settings.AWS_BUCKET_NAME,
                        Key=obj['Key']
                    )
                    
                    backups.append({
                        "filename": obj['Key'].split('/')[-1],
                        "s3_key": obj['Key'],
                        "size_bytes": obj['Size'],
                        "size_mb": round(obj['Size'] / 1024 / 1024, 2),
                        "last_modified": obj['LastModified'].isoformat(),
                        "metadata": head_response.get('Metadata', {}),
                        "location": "s3"
                    })
            else:
                # List local backups
                backup_dir = Path("/tmp")
                backup_files = list(backup_dir.glob("comptaflow_backup_*.sql"))
                
                for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / 1024 / 1024, 2),
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "location": "local"
                    })
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    async def restore_backup(self, backup_filename: str) -> Dict:
        """Restore database from backup"""
        try:
            self.logger.warning(f"Starting database restore from: {backup_filename}")
            
            # Download from S3 if needed
            local_backup_path = f"/tmp/{backup_filename}"
            
            if self.s3_client and settings.AWS_BUCKET_NAME:
                s3_key = f"backups/database/{backup_filename}"
                
                self.s3_client.download_file(
                    settings.AWS_BUCKET_NAME,
                    s3_key,
                    local_backup_path
                )
            
            # Parse database URL
            db_url = settings.DATABASE_URL
            url_parts = db_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
            user_pass, host_db = url_parts.split("@")
            user, password = user_pass.split(":")
            host_port, dbname = host_db.split("/")
            host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")
            
            # Create psql restore command
            psql_cmd = [
                "psql",
                f"--host={host}",
                f"--port={port}",
                f"--username={user}",
                f"--dbname={dbname}",
                "--no-password",
                f"--file={local_backup_path}"
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            # Execute restore
            process = subprocess.run(
                psql_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if process.returncode != 0:
                raise Exception(f"psql restore failed: {process.stderr}")
            
            # Clean up downloaded file
            if os.path.exists(local_backup_path):
                os.remove(local_backup_path)
            
            self.logger.info(f"Database restore completed: {backup_filename}")
            
            return {
                "status": "completed",
                "backup_filename": backup_filename,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Database restored successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Database restore failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_backups(self, retention_days: int = 30) -> Dict:
        """Clean up backups older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = 0
            
            if self.s3_client and settings.AWS_BUCKET_NAME:
                # Clean up S3 backups
                response = self.s3_client.list_objects_v2(
                    Bucket=settings.AWS_BUCKET_NAME,
                    Prefix="backups/database/"
                )
                
                for obj in response.get('Contents', []):
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        self.s3_client.delete_object(
                            Bucket=settings.AWS_BUCKET_NAME,
                            Key=obj['Key']
                        )
                        deleted_count += 1
                        self.logger.info(f"Deleted old backup: {obj['Key']}")
            
            return {
                "status": "completed",
                "deleted_count": deleted_count,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def get_backup_status(self) -> Dict:
        """Get overall backup system status"""
        try:
            backups = await self.list_backups(limit=5)
            
            # Calculate backup health metrics
            if not backups:
                status = "warning"
                message = "No backups found"
                last_backup_age = None
            else:
                latest_backup = backups[0]
                last_backup_time = datetime.fromisoformat(latest_backup['last_modified'].replace('Z', '+00:00'))
                last_backup_age = datetime.utcnow().replace(tzinfo=last_backup_time.tzinfo) - last_backup_time
                
                if last_backup_age.total_seconds() < 24 * 3600:  # Less than 24 hours
                    status = "healthy"
                    message = "Recent backup available"
                elif last_backup_age.total_seconds() < 7 * 24 * 3600:  # Less than 7 days
                    status = "warning" 
                    message = "Backup older than 24 hours"
                else:
                    status = "critical"
                    message = "Backup older than 7 days"
            
            return {
                "status": status,
                "message": message,
                "backup_count": len(backups),
                "last_backup_age_hours": last_backup_age.total_seconds() / 3600 if last_backup_age else None,
                "s3_configured": bool(self.s3_client and settings.AWS_BUCKET_NAME),
                "latest_backups": backups[:3]  # Show latest 3 backups
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Global backup manager instance
backup_manager = BackupManager()


# CLI-style functions for manual backup operations
async def create_manual_backup():
    """Create a manual backup"""
    return await backup_manager.create_database_backup("manual")


async def schedule_automated_backups():
    """Setup automated backup scheduling (requires external cron or task scheduler)"""
    # This would typically be called by a cron job or task scheduler
    return await backup_manager.create_database_backup("scheduled")


async def restore_latest_backup():
    """Restore from the latest backup"""
    backups = await backup_manager.list_backups(limit=1)
    if not backups:
        return {"status": "error", "message": "No backups available"}
    
    latest_backup = backups[0]
    return await backup_manager.restore_backup(latest_backup['filename'])