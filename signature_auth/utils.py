import secrets
import hmac
import hashlib
import time
from typing import Dict, Any, Optional


def generate_secret_key(length: int = 64) -> str:
    """
    Generate cryptographically secure secret key

    Args:
        length: Length of the key in characters

    Returns:
        URL-safe base64 encoded random key
    """
    return secrets.token_urlsafe(length)


def verify_response_signature(response_content: str, status_code: int,
                              signature: str, timestamp: str, nonce: str,
                              secret_key: str) -> bool:
    """
    Verify response signature from signature-protected endpoint

    Args:
        response_content: Response body content
        status_code: HTTP status code
        signature: Signature from X-Signature header
        timestamp: Timestamp from X-Timestamp header
        nonce: Nonce from X-Nonce header
        secret_key: Secret key for verification

    Returns:
        True if signature is valid
    """
    try:
        # Reconstruct the signed message
        message = f"{status_code}|{response_content}|{timestamp}|{nonce}"

        # Calculate expected signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Compare signatures securely
        return hmac.compare_digest(signature, expected_signature)

    except Exception:
        return False


def create_manual_signature(method: str, path: str, body: Any = None,
                            secret_key: str = None, timestamp: int = None,
                            nonce: str = None) -> Dict[str, str]:
    """
    Manually create signature headers for custom implementations

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        body: Request body (optional)
        secret_key: Secret key for signing
        timestamp: Unix timestamp (auto-generated if None)
        nonce: Unique nonce (auto-generated if None)

    Returns:
        Dictionary with signature headers
    """
    import json
    import uuid

    if not secret_key:
        raise ValueError("Secret key is required")

    if timestamp is None:
        timestamp = int(time.time())

    if nonce is None:
        nonce = str(uuid.uuid4())

    # Normalize body
    body_str = ""
    if body is not None:
        if isinstance(body, dict):
            body_str = json.dumps(body, separators=(',', ':'), sort_keys=True, ensure_ascii=True)
        elif isinstance(body, str):
            body_str = body
        else:
            body_str = str(body)

    # Create message
    message = f"{method.upper()}|{path}|{body_str}|{timestamp}|{nonce}"

    # Calculate signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return {
        'X-Signature': signature,
        'X-Timestamp': str(timestamp),
        'X-Nonce': nonce
    }


class SignatureHelper:
    """
    Helper class for signature operations
    Useful for custom integrations
    """

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

        if not self.secret_key:
            raise ValueError("Secret key is required")

    def sign_request(self, method: str, path: str, body: Any = None) -> Dict[str, str]:
        """Create signature headers for request"""
        return create_manual_signature(method, path, body, self.secret_key)

    def verify_response(self, response_content: str, status_code: int,
                        signature: str, timestamp: str, nonce: str) -> bool:
        """Verify response signature"""
        return verify_response_signature(
            response_content, status_code, signature,
            timestamp, nonce, self.secret_key
        )

    def is_signature_expired(self, timestamp: str, max_age: int = 300) -> bool:
        """Check if signature timestamp is expired"""
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            return (current_time - request_time) > max_age
        except (ValueError, TypeError):
            return True


def validate_secret_key(secret_key: str) -> Dict[str, Any]:
    """
    Validate secret key strength and provide recommendations

    Args:
        secret_key: Secret key to validate

    Returns:
        Dictionary with validation results and recommendations
    """
    result = {
        'valid': True,
        'strength': 'unknown',
        'warnings': [],
        'recommendations': []
    }

    if not secret_key:
        result['valid'] = False
        result['strength'] = 'invalid'
        result['warnings'].append('Secret key is empty')
        return result

    # Check length
    if len(secret_key) < 32:
        result['warnings'].append('Secret key is shorter than recommended (32+ characters)')
        result['strength'] = 'weak'
    elif len(secret_key) < 64:
        result['strength'] = 'medium'
    else:
        result['strength'] = 'strong'

    # Check for obvious weak patterns
    weak_patterns = [
        'password', 'secret', 'key', 'test', 'demo', 'example',
        '123456', 'qwerty', 'abc', 'admin'
    ]

    key_lower = secret_key.lower()
    for pattern in weak_patterns:
        if pattern in key_lower:
            result['warnings'].append(f'Contains weak pattern: {pattern}')
            result['strength'] = 'weak'

    # Recommendations
    if result['strength'] == 'weak':
        result['recommendations'].append('Generate a new key using generate_secret_key()')

    if len(secret_key) < 64:
        result['recommendations'].append('Use at least 64 characters for production')

    return result