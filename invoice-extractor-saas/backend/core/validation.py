"""
Input validation and sanitization utilities for InvoiceAI
Provides GDPR-compliant validation with security considerations
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, validator

from core.exceptions import ValidationError


class ValidationRules:
    """Centralized validation rules for the application"""
    
    # Regex patterns
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+\.(pdf|png|jpg|jpeg)$', re.IGNORECASE)
    
    # Size limits
    MAX_STRING_LENGTH = 1000
    MAX_TEXT_LENGTH = 10000
    MAX_EMAIL_LENGTH = 254
    MAX_FILENAME_LENGTH = 255
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Allowed values
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg", 
        "image/png",
        "image/jpg"
    }
    
    ALLOWED_INVOICE_STATUSES = {
        "pending",
        "processing", 
        "completed",
        "failed"
    }
    
    ALLOWED_DATA_SUBJECT_TYPES = {
        "business_contact",
        "individual_contractor",
        "employee", 
        "customer_representative"
    }


def validate_uuid(value: str, field_name: str = "UUID") -> uuid.UUID:
    """Validate and convert string to UUID"""
    if not value:
        raise ValidationError(f"{field_name} is required")
    
    if isinstance(value, uuid.UUID):
        return value
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if not ValidationRules.UUID_PATTERN.match(value):
        raise ValidationError(f"Invalid {field_name} format")
    
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ValidationError(f"Invalid {field_name} format")


def validate_email_address(email: str, field_name: str = "email") -> str:
    """Validate email address format"""
    if not email:
        raise ValidationError(f"{field_name} is required")
    
    if not isinstance(email, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if len(email) > ValidationRules.MAX_EMAIL_LENGTH:
        raise ValidationError(f"{field_name} is too long (max {ValidationRules.MAX_EMAIL_LENGTH} characters)")
    
    try:
        # Use email-validator for comprehensive validation
        validated_email = validate_email(email)
        return validated_email.email.lower()  # Normalize to lowercase
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid {field_name} format: {str(e)}")


def validate_string(
    value: str, 
    field_name: str,
    min_length: int = 1,
    max_length: int = None,
    pattern: re.Pattern = None,
    required: bool = True
) -> Optional[str]:
    """Validate string input with various constraints"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    # Trim whitespace
    value = value.strip()
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long")
    
    max_len = max_length or ValidationRules.MAX_STRING_LENGTH
    if len(value) > max_len:
        raise ValidationError(f"{field_name} is too long (max {max_len} characters)")
    
    if pattern and not pattern.match(value):
        raise ValidationError(f"{field_name} format is invalid")
    
    # Basic sanitization - remove potential harmful characters
    if any(char in value for char in ['<', '>', '"', "'"]):
        raise ValidationError(f"{field_name} contains invalid characters")
    
    return value


def validate_filename(filename: str) -> str:
    """Validate uploaded filename"""
    validated = validate_string(
        filename,
        "filename",
        min_length=1,
        max_length=ValidationRules.MAX_FILENAME_LENGTH,
        pattern=ValidationRules.FILENAME_PATTERN
    )
    
    # Additional security checks
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError("Filename contains invalid path characters")
    
    return validated


def validate_mime_type(mime_type: str) -> str:
    """Validate file MIME type"""
    if not mime_type:
        raise ValidationError("MIME type is required")
    
    if mime_type not in ValidationRules.ALLOWED_MIME_TYPES:
        raise ValidationError(f"Unsupported file type: {mime_type}")
    
    return mime_type


def validate_file_size(size: int) -> int:
    """Validate file size"""
    if not isinstance(size, int) or size < 0:
        raise ValidationError("Invalid file size")
    
    if size > ValidationRules.MAX_FILE_SIZE:
        raise ValidationError(f"File too large (max {ValidationRules.MAX_FILE_SIZE // (1024*1024)}MB)")
    
    return size


def validate_invoice_status(status: str) -> str:
    """Validate invoice processing status"""
    if not status:
        raise ValidationError("Status is required")
    
    if status not in ValidationRules.ALLOWED_INVOICE_STATUSES:
        raise ValidationError(f"Invalid status: {status}")
    
    return status


def validate_data_subject_type(subject_type: str) -> str:
    """Validate data subject type"""
    if not subject_type:
        raise ValidationError("Data subject type is required")
    
    if subject_type not in ValidationRules.ALLOWED_DATA_SUBJECT_TYPES:
        raise ValidationError(f"Invalid data subject type: {subject_type}")
    
    return subject_type


def validate_pagination(skip: int = 0, limit: int = 100) -> tuple:
    """Validate pagination parameters"""
    if not isinstance(skip, int) or skip < 0:
        raise ValidationError("Skip must be a non-negative integer")
    
    if not isinstance(limit, int) or limit < 1:
        raise ValidationError("Limit must be a positive integer")
    
    if limit > 1000:  # Prevent excessive data retrieval
        raise ValidationError("Limit too high (max 1000)")
    
    return skip, limit


def validate_json_data(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """Validate JSON data structure"""
    if not isinstance(data, dict):
        raise ValidationError("Data must be a JSON object")
    
    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            raise ValidationError(f"JSON too deeply nested (max depth {max_depth})")
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    raise ValidationError("JSON keys must be strings")
                check_depth(value, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, current_depth + 1)
    
    check_depth(data)
    return data


def sanitize_search_query(query: str) -> str:
    """Sanitize search query to prevent injection attacks"""
    if not query:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', query.strip())
    
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized


def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> tuple:
    """Validate date range parameters"""
    if start_date and end_date:
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        # Prevent excessively large date ranges (e.g., more than 2 years)
        if (end_date - start_date).days > 730:
            raise ValidationError("Date range too large (max 2 years)")
    
    return start_date, end_date


def validate_processing_purposes(purposes: List[str]) -> List[str]:
    """Validate processing purposes for GDPR compliance"""
    if not purposes:
        raise ValidationError("At least one processing purpose is required")
    
    if not isinstance(purposes, list):
        raise ValidationError("Processing purposes must be a list")
    
    valid_purposes = {
        "invoice_processing",
        "business_operations", 
        "accounting",
        "ai_processing",
        "data_analysis",
        "customer_service",
        "legal_compliance"
    }
    
    validated_purposes = []
    for purpose in purposes:
        if not isinstance(purpose, str):
            raise ValidationError("Processing purpose must be a string")
        
        purpose = purpose.lower().strip()
        if purpose not in valid_purposes:
            raise ValidationError(f"Invalid processing purpose: {purpose}")
        
        if purpose not in validated_purposes:  # Avoid duplicates
            validated_purposes.append(purpose)
    
    return validated_purposes


def validate_legal_basis(legal_basis: str) -> str:
    """Validate legal basis for GDPR compliance"""
    valid_bases = {
        "consent",
        "contract",
        "legal_obligation", 
        "vital_interests",
        "public_task",
        "legitimate_interest"
    }
    
    if not legal_basis:
        raise ValidationError("Legal basis is required")
    
    basis = legal_basis.lower().strip()
    if basis not in valid_bases:
        raise ValidationError(f"Invalid legal basis: {legal_basis}")
    
    return basis


# Security validation functions
def validate_password_strength(password: str) -> str:
    """Validate password meets security requirements"""
    if not password:
        raise ValidationError("Password is required")
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    
    if len(password) > 128:
        raise ValidationError("Password is too long (max 128 characters)")
    
    # Check for at least one uppercase, lowercase, digit, and special character
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        raise ValidationError("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        raise ValidationError("Password must contain at least one special character")
    
    return password


def validate_ip_address(ip: str) -> str:
    """Validate IP address format"""
    if not ip:
        return None
    
    # Basic IPv4/IPv6 validation
    ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    ipv6_pattern = re.compile(r'^([0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}$', re.IGNORECASE)
    
    if not (ipv4_pattern.match(ip) or ipv6_pattern.match(ip)):
        raise ValidationError("Invalid IP address format")
    
    return ip