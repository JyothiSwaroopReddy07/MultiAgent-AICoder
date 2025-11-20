"""
Input Validation Utilities
- Request validation
- Data sanitization
- Type checking
"""
from typing import Any, Optional
import re
from constants import (
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    ErrorMessages
)


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_description(description: str) -> tuple[bool, Optional[str]]:
    """
    Validate project description
    
    Args:
        description: Project description string
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        is_valid, error = validate_description(user_input)
        if not is_valid:
            raise ValidationError(error)
    """
    if not description or not isinstance(description, str):
        return False, "Description must be a non-empty string"
    
    description = description.strip()
    
    if len(description) < MIN_DESCRIPTION_LENGTH:
        return False, ErrorMessages.INVALID_DESCRIPTION.format(
            min=MIN_DESCRIPTION_LENGTH,
            max=MAX_DESCRIPTION_LENGTH
        )
    
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False, ErrorMessages.INVALID_DESCRIPTION.format(
            min=MIN_DESCRIPTION_LENGTH,
            max=MAX_DESCRIPTION_LENGTH
        )
    
    # Check for suspicious content
    if contains_sql_injection(description):
        return False, "Description contains potentially malicious SQL patterns"
    
    if contains_xss(description):
        return False, "Description contains potentially malicious script patterns"
    
    return True, None


def validate_database_preference(db_preference: str) -> tuple[bool, Optional[str]]:
    """
    Validate database preference
    
    Args:
        db_preference: Database preference ('auto', 'postgresql', 'mongodb')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_preferences = ['auto', 'postgresql', 'mongodb']
    
    if not db_preference or not isinstance(db_preference, str):
        return False, "Database preference must be a string"
    
    db_preference = db_preference.lower().strip()
    
    if db_preference not in valid_preferences:
        return False, ErrorMessages.INVALID_DATABASE.format(db_type=db_preference)
    
    return True, None


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input
    
    Args:
        text: Input string
        max_length: Maximum length (optional)
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Trim to max length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def contains_sql_injection(text: str) -> bool:
    """
    Check for potential SQL injection patterns
    
    Args:
        text: Input text
        
    Returns:
        True if suspicious patterns found
    """
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bUNION\b.*\bSELECT\b)",
    ]
    
    text_upper = text.upper()
    
    for pattern in sql_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return True
    
    return False


def contains_xss(text: str) -> bool:
    """
    Check for potential XSS patterns
    
    Args:
        text: Input text
        
    Returns:
        True if suspicious patterns found
    """
    xss_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<embed",
        r"<object",
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def validate_json_structure(data: dict, required_keys: list[str]) -> tuple[bool, Optional[str]]:
    """
    Validate JSON structure has required keys
    
    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        return False, f"Missing required keys: {', '.join(missing_keys)}"
    
    return True, None


def validate_file_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate file path for security
    
    Args:
        path: File path
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path or not isinstance(path, str):
        return False, "Path must be a non-empty string"
    
    # Check for path traversal
    if ".." in path:
        return False, "Path traversal not allowed"
    
    # Check for absolute paths (should be relative)
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False, "Absolute paths not allowed"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r"\$\{",  # Variable substitution
        r"`",     # Command execution
        r"\|",    # Pipe
        r"&",     # Command chaining
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, path):
            return False, f"Suspicious pattern in path: {pattern}"
    
    return True, None


def validate_port(port: Any) -> tuple[bool, Optional[str]]:
    """
    Validate port number
    
    Args:
        port: Port number
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        port_int = int(port)
        if 1 <= port_int <= 65535:
            return True, None
        return False, "Port must be between 1 and 65535"
    except (ValueError, TypeError):
        return False, "Port must be a valid integer"


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format
    
    Args:
        email: Email address
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email must be a non-empty string"
    
    # Simple email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    return True, None


class RequestValidator:
    """
    Request validation class for API endpoints
    
    Example:
        validator = RequestValidator()
        validator.validate_generation_request({
            "description": "Build a todo app",
            "database_preference": "auto"
        })
    """
    
    @staticmethod
    def validate_generation_request(data: dict) -> None:
        """
        Validate code generation request
        
        Args:
            data: Request data
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required keys
        is_valid, error = validate_json_structure(data, ["description"])
        if not is_valid:
            raise ValidationError(error)
        
        # Validate description
        is_valid, error = validate_description(data["description"])
        if not is_valid:
            raise ValidationError(error)
        
        # Validate database preference if provided
        if "database_preference" in data:
            is_valid, error = validate_database_preference(data["database_preference"])
            if not is_valid:
                raise ValidationError(error)
    
    @staticmethod
    def validate_clarification_request(data: dict) -> None:
        """
        Validate clarification request
        
        Args:
            data: Request data
            
        Raises:
            ValidationError: If validation fails
        """
        is_valid, error = validate_json_structure(
            data,
            ["request_id", "clarifications"]
        )
        if not is_valid:
            raise ValidationError(error)
        
        if not isinstance(data["clarifications"], list):
            raise ValidationError("Clarifications must be a list")
        
        for clarification in data["clarifications"]:
            if not isinstance(clarification, dict):
                raise ValidationError("Each clarification must be a dictionary")
            
            is_valid, error = validate_json_structure(
                clarification,
                ["question_id", "answer"]
            )
            if not is_valid:
                raise ValidationError(error)

