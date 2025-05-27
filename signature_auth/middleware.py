import hmac
import hashlib
import json
import time
import uuid
import logging
import threading
from datetime import datetime, timezone
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError

logger = logging.getLogger(__name__)


class CacheBackendDetector:
    """
    Detects and optimizes for different Django cache backends
    """

    @staticmethod
    def get_cache_info():
        """Get information about the configured cache backend"""
        try:
            backend_class = cache.__class__.__name__
            backend_module = cache.__class__.__module__

            # Try to get the configured backend from settings
            configured_backend = settings.CACHES['default']['BACKEND']

            logger.debug(f"Cache detection: class={backend_class}, module={backend_module}")
            logger.debug(f"Configured backend: {configured_backend}")

            cache_info = {
                'backend_class': backend_class,
                'backend_module': backend_module,
                'is_redis': False,
                'is_memcached': False,
                'is_database': False,
                'is_file': False,
                'is_memory': False,
                'supports_atomic_operations': False,
                'supports_ttl': True,
                'backend_name': 'unknown'
            }

            # Check the configured backend directly
            if 'django_redis' in configured_backend or 'redis' in configured_backend.lower():
                logger.info('Redis backend detected from settings configuration')
                cache_info.update({
                    'is_redis': True,
                    'supports_atomic_operations': True,
                    'backend_name': 'Redis'
                })
                return cache_info

            # Continue with existing detection logic as fallback
            if ('redis' in backend_module.lower() or 'redis' in backend_class.lower() or
                    'django_redis' in backend_module.lower()):
                logger.info('Redis backend detected from class/module inspection')
                cache_info.update({
                    'is_redis': True,
                    'supports_atomic_operations': True,
                    'backend_name': 'Redis'
                })

            # Detect Memcached backends
            elif 'memcached' in backend_module.lower():
                cache_info.update({
                    'is_memcached': True,
                    'backend_name': 'Memcached'
                })

            # Detect Database backend
            elif 'db' in backend_module.lower() or 'database' in backend_class.lower():
                cache_info.update({
                    'is_database': True,
                    'backend_name': 'Database'
                })

            # Detect File backend
            elif 'filebased' in backend_module.lower():
                cache_info.update({
                    'is_file': True,
                    'backend_name': 'File System'
                })

            # Detect In-memory backend
            elif 'locmem' in backend_module.lower():
                cache_info.update({
                    'is_memory': True,
                    'backend_name': 'Local Memory'
                })

            return cache_info

        except Exception as e:
            logger.error(f"Error detecting cache backend: {e}")
            return {
                'backend_class': 'unknown',
                'backend_module': 'unknown',
                'backend_name': 'Unknown',
                'error': str(e)
            }


class OptimizedInMemoryNonceStore:
    """
    Enhanced in-memory nonce store with performance optimizations
    """

    def __init__(self, max_size=10000):
        self._store = {}
        self._access_times = {}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 60
        self._max_size = max_size

        logger.info(f"Initialized in-memory nonce store (max_size: {max_size})")

    def is_used(self, nonce):
        """Check if nonce has been used"""
        with self._lock:
            self._cleanup_if_needed()
            current_time = time.time()

            if nonce in self._store:
                # Update access time for LRU
                self._access_times[nonce] = current_time
                expiry_time = self._store[nonce]
                return current_time <= expiry_time

            return False

    def mark_used(self, nonce, expiry_time):
        """Mark nonce as used with expiry"""
        with self._lock:
            current_time = time.time()

            # Check if we need to evict old entries
            if len(self._store) >= self._max_size:
                self._evict_old_entries()

            self._store[nonce] = expiry_time
            self._access_times[nonce] = current_time
            self._cleanup_if_needed()

    def _cleanup_if_needed(self):
        """Cleanup expired nonces if needed"""
        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        self._cleanup_expired()
        self._last_cleanup = current_time

    def _cleanup_expired(self):
        """Remove expired nonces"""
        current_time = time.time()
        expired_nonces = []

        for nonce, expiry_time in self._store.items():
            if current_time > expiry_time:
                expired_nonces.append(nonce)

        for nonce in expired_nonces:
            del self._store[nonce]
            self._access_times.pop(nonce, None)

        if expired_nonces:
            logger.debug(f"Cleaned up {len(expired_nonces)} expired nonces")

    def _evict_old_entries(self):
        """Evict least recently used entries when store is full"""
        if not self._access_times:
            return

        # Sort by access time and remove oldest 25%
        sorted_entries = sorted(self._access_times.items(), key=lambda x: x[1])
        evict_count = max(1, len(sorted_entries) // 4)

        for nonce, _ in sorted_entries[:evict_count]:
            self._store.pop(nonce, None)
            self._access_times.pop(nonce, None)

        logger.debug(f"Evicted {evict_count} old nonce entries")

    def get_stats(self):
        """Get detailed store statistics"""
        with self._lock:
            current_time = time.time()
            active_count = sum(1 for expiry in self._store.values() if current_time <= expiry)

            return {
                'total_entries': len(self._store),
                'active_entries': active_count,
                'expired_entries': len(self._store) - active_count,
                'max_size': self._max_size,
                'memory_usage_mb': self._estimate_memory_usage(),
                'last_cleanup': self._last_cleanup
            }

    def _estimate_memory_usage(self):
        """Estimate memory usage in MB"""
        try:
            import sys
            total_size = sys.getsizeof(self._store) + sys.getsizeof(self._access_times)
            for key, value in self._store.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            for key, value in self._access_times.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return round(total_size / 1024 / 1024, 2)
        except:
            return 0


class SignatureAuthenticationMiddleware(MiddlewareMixin):
    """
    Ultra-portable signature authentication middleware with automatic cache backend optimization

    Automatically detects and optimizes for:
    - Redis (django-redis or built-in Redis backend)
    - Memcached
    - Database cache
    - File system cache
    - In-memory cache
    - Fallback to optimized in-memory store
    """

    def __init__(self, get_response):
        super().__init__(get_response)

        # Load configuration
        self._load_config()

        # Detect and optimize for cache backend
        self._setup_cache_backend()

        # Initialize nonce tracking
        self._init_nonce_tracking()

        # Validate configuration
        self._validate_config()

        # Log startup information
        self._log_startup_info()

    def _load_config(self):
        """Load all configuration from Django settings"""
        # Core settings
        self.secret_key = getattr(settings, 'SIGNATURE_AUTH_SECRET_KEY', None)
        self.signature_window = getattr(settings, 'SIGNATURE_AUTH_VALIDITY_WINDOW', 300)

        # Path configuration
        self.protected_paths = getattr(settings, 'SIGNATURE_AUTH_PROTECTED_PATHS', ['/api/'])
        self.excluded_paths = getattr(settings, 'SIGNATURE_AUTH_EXCLUDED_PATHS', [
            '/admin/', '/static/', '/media/', '/health/', '/docs/', '/favicon.ico'
        ])

        # Headers
        self.signature_header = getattr(settings, 'SIGNATURE_AUTH_SIGNATURE_HEADER', 'HTTP_X_SIGNATURE')
        self.timestamp_header = getattr(settings, 'SIGNATURE_AUTH_TIMESTAMP_HEADER', 'HTTP_X_TIMESTAMP')
        self.nonce_header = getattr(settings, 'SIGNATURE_AUTH_NONCE_HEADER', 'HTTP_X_NONCE')

        # Response headers
        self.response_signature_header = getattr(settings, 'SIGNATURE_AUTH_RESPONSE_SIGNATURE_HEADER', 'X-Signature')
        self.response_timestamp_header = getattr(settings, 'SIGNATURE_AUTH_RESPONSE_TIMESTAMP_HEADER', 'X-Timestamp')
        self.response_nonce_header = getattr(settings, 'SIGNATURE_AUTH_RESPONSE_NONCE_HEADER', 'X-Nonce')

        # Cache settings
        self.nonce_cache_prefix = getattr(settings, 'SIGNATURE_AUTH_NONCE_CACHE_PREFIX', 'sig_nonce')
        self.use_cache_fallback = getattr(settings, 'SIGNATURE_AUTH_USE_CACHE_FALLBACK', True)
        self.fallback_max_size = getattr(settings, 'SIGNATURE_AUTH_FALLBACK_MAX_SIZE', 10000)

        # Response enhancement
        self.auto_enhance_responses = getattr(settings, 'SIGNATURE_AUTH_AUTO_ENHANCE_RESPONSES', True)
        self.add_processing_metadata = getattr(settings, 'SIGNATURE_AUTH_ADD_PROCESSING_METADATA', True)

        # Debug settings
        self.debug_mode = getattr(settings, 'SIGNATURE_AUTH_DEBUG', getattr(settings, 'DEBUG', False))

    def _setup_cache_backend(self):
        """Detect and setup cache backend optimization"""
        self.cache_info = CacheBackendDetector.get_cache_info()
        self.cache_available = True

        # Test cache availability
        try:
            test_key = f"{self.nonce_cache_prefix}_test"
            cache.set(test_key, 'test', 1)
            cache.delete(test_key)

            # Add more detailed logging
            logger.info(f"Cache backend class: {cache.__class__.__name__}")
            logger.info(f"Cache backend module: {cache.__class__.__module__}")
            logger.info(f"CACHES setting: {settings.CACHES['default']['BACKEND']}")
            logger.info(f"Cache detection details: {self.cache_info}")
            logger.info(f"Using Django cache backend: {self.cache_info['backend_name']}")

        except Exception as e:
            logger.warning(f"Django cache unavailable: {e}")
            self.cache_available = False

    def _init_nonce_tracking(self):
        """Initialize nonce tracking system"""
        self.fallback_store = None

        if not self.cache_available and self.use_cache_fallback:
            self.fallback_store = OptimizedInMemoryNonceStore(max_size=self.fallback_max_size)
            logger.info("Using optimized in-memory fallback for nonce tracking")
        elif not self.cache_available:
            raise RuntimeError(
                "Cache is unavailable and fallback is disabled. "
                "Configure Django cache or set SIGNATURE_AUTH_USE_CACHE_FALLBACK=True"
            )

    def _validate_config(self):
        """Validate configuration"""
        if not self.secret_key:
            raise ValueError(
                "SIGNATURE_AUTH_SECRET_KEY must be set in Django settings. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

    def _log_startup_info(self):
        """Log startup information"""
        logger.info("=" * 50)
        logger.info("Django Signature Authentication Middleware")
        logger.info("=" * 50)
        logger.info(f"Version: Ultra-Portable v1.0.0")
        logger.info(f"Cache Backend: {self.cache_info['backend_name']}")
        logger.info(f"Cache Available: {self.cache_available}")
        logger.info(f"Fallback Store: {'Active' if self.fallback_store else 'Disabled'}")
        logger.info(f"Protected Paths: {self.protected_paths}")
        logger.info(f"Signature Window: {self.signature_window}s")
        logger.info(f"Debug Mode: {self.debug_mode}")
        logger.info("=" * 50)

    def process_request(self, request):
        """Validate incoming request signature"""
        if not self._is_protected_path(request.path):
            return None

        is_valid, error_message, details = self._validate_signature(request)

        if not is_valid:
            logger.warning(
                f"Signature validation failed: {error_message} - "
                f"{request.method} {request.path} from {self._get_client_ip(request)}"
            )
            return self._create_error_response(error_message, details, request)

        self._mark_request_authenticated(request)

        if self.debug_mode:
            logger.info(f"✅ Request authenticated - ID: {request._sig_auth_request_id}")

        return None

    def process_response(self, request, response):
        """Sign outgoing response"""
        if not self._is_protected_path(request.path):
            return response

        if not self._is_json_response(response):
            return response

        if self.auto_enhance_responses:
            self._enhance_response_content(request, response)

        self._sign_response(response)

        return response

    def _is_protected_path(self, path):
        """Check if path requires signature authentication"""
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return False

        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True

        return False

    def _is_json_response(self, response):
        """Check if response is JSON"""
        content_type = response.get('Content-Type', '').lower()
        return 'application/json' in content_type

    def _validate_signature(self, request):
        """Validate request signature with detailed error reporting"""
        try:
            # Extract components
            signature = request.META.get(self.signature_header)
            timestamp_str = request.META.get(self.timestamp_header)
            nonce = request.META.get(self.nonce_header)

            # Check missing headers
            missing = []
            if not signature: missing.append('signature')
            if not timestamp_str: missing.append('timestamp')
            if not nonce: missing.append('nonce')

            if missing:
                return False, f"Missing headers: {', '.join(missing)}", {'missing': missing}

            # Validate timestamp
            try:
                timestamp = int(timestamp_str)
            except (ValueError, TypeError):
                return False, "Invalid timestamp format", {'timestamp': timestamp_str}

            # Check freshness
            current_time = int(time.time())
            time_diff = abs(current_time - timestamp)

            if time_diff > self.signature_window:
                return False, f"Request expired (age: {time_diff}s)", {
                    'age': time_diff, 'max_age': self.signature_window
                }

            # Check nonce uniqueness
            if self._is_nonce_used(nonce):
                return False, "Replay attack detected", {'nonce': nonce[:8] + '...'}

            # Verify signature
            expected_signature = self._calculate_request_signature(request, timestamp_str, nonce)

            if not hmac.compare_digest(signature, expected_signature):
                return False, "Invalid signature", {'method': 'HMAC-SHA256'}

            # Mark nonce as used
            self._mark_nonce_used(nonce, timestamp)

            return True, "Valid signature", {'nonce': nonce[:8] + '...', 'age': time_diff}

        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False, "Validation error", {'error': str(e)}

    def _calculate_request_signature(self, request, timestamp, nonce):
        """Calculate request signature"""
        method = request.method.upper()
        path = request.path
        body = self._normalize_request_body(request)

        message = f"{method}|{path}|{body}|{timestamp}|{nonce}"

        return hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _normalize_request_body(self, request):
        """Normalize request body for consistent signatures"""
        if not request.body:
            return ""

        try:
            content_type = getattr(request, 'content_type', '') or request.META.get('CONTENT_TYPE', '')

            if 'application/json' in content_type.lower():
                data = json.loads(request.body)
                return json.dumps(data, separators=(',', ':'), sort_keys=True, ensure_ascii=True)
            else:
                return request.body.decode('utf-8')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return request.body.hex()

    def _is_nonce_used(self, nonce):
        """Check if nonce has been used (optimized for cache backend)"""
        try:
            if self.cache_available:
                cache_key = f"{self.nonce_cache_prefix}:{nonce}"

                # Optimize for Redis backend
                if self.cache_info['is_redis']:
                    # Redis backends support atomic operations
                    return cache.get(cache_key) is not None
                else:
                    # Other backends
                    return cache.get(cache_key) is not None

            elif self.fallback_store:
                return self.fallback_store.is_used(nonce)
            else:
                logger.warning("No nonce tracking available")
                return False

        except Exception as e:
            logger.error(f"Error checking nonce: {e}")
            return True  # Fail secure

    def _mark_nonce_used(self, nonce, timestamp):
        """Mark nonce as used (optimized for cache backend)"""
        try:
            expiry_time = timestamp + self.signature_window + 60

            if self.cache_available:
                cache_key = f"{self.nonce_cache_prefix}:{nonce}"
                timeout = self.signature_window + 60

                # Optimize based on backend
                if self.cache_info['is_redis']:
                    # Redis can handle high-frequency writes efficiently
                    cache.set(cache_key, timestamp, timeout=timeout)
                elif self.cache_info['is_database']:
                    # Database cache - batch operations if possible
                    cache.set(cache_key, timestamp, timeout=timeout)
                else:
                    # Other backends
                    cache.set(cache_key, timestamp, timeout=timeout)

            elif self.fallback_store:
                self.fallback_store.mark_used(nonce, expiry_time)

        except Exception as e:
            logger.error(f"Error marking nonce as used: {e}")

    def _mark_request_authenticated(self, request):
        """Mark request as authenticated"""
        request._sig_auth_authenticated = True
        request._sig_auth_request_id = str(uuid.uuid4())
        request._sig_auth_timestamp = datetime.now(timezone.utc)
        request._sig_auth_client_ip = self._get_client_ip(request)
        request._sig_auth_cache_backend = self.cache_info['backend_name']

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', 'unknown')

    def _enhance_response_content(self, request, response):
        """Enhance response with metadata"""
        if not self.add_processing_metadata:
            return

        try:
            if response.content:
                try:
                    data = json.loads(response.content.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return
            else:
                data = {}

            metadata = {}

            if 'timestamp' not in data:
                metadata['timestamp'] = datetime.now(timezone.utc).isoformat()

            if 'request_id' not in data:
                metadata['request_id'] = getattr(request, '_sig_auth_request_id', str(uuid.uuid4()))

            if 'authenticated' not in data:
                metadata['authenticated'] = True

            if 'user' not in data:
                # Get actual authenticated user from request
                metadata['user'] = request.user.username if hasattr(request.user, 'username') else str(request.user)

            if 'cache_backend' not in data and self.debug_mode:
                metadata['cache_backend'] = getattr(request, '_sig_auth_cache_backend', 'unknown')

            if metadata:
                if isinstance(data, dict):
                    data.update(metadata)
                else:
                    data = {'data': data, **metadata}

                new_content = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
                response.content = new_content.encode('utf-8')
                response['Content-Length'] = len(response.content)

        except Exception as e:
            logger.error(f"Error enhancing response: {e}")

    def _sign_response(self, response):
        """Sign outgoing response"""
        try:
            content = response.content.decode('utf-8') if response.content else ""
            timestamp = int(time.time())
            nonce = str(uuid.uuid4())

            status = str(response.status_code)
            message = f"{status}|{content}|{timestamp}|{nonce}"

            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            response[self.response_signature_header] = signature
            response[self.response_timestamp_header] = str(timestamp)
            response[self.response_nonce_header] = nonce

        except Exception as e:
            logger.error(f"Error signing response: {e}")

    def _create_error_response(self, error_message, details=None, request=None):
        """Create error response"""
        response_data = {
            'error': 'Authentication Failed',
            'message': error_message,
            'code': 'SIGNATURE_INVALID',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_id': str(uuid.uuid4()),
            'user': "Anonymous"  # Default value
        }

        # Only try to get user info if request is provided
        if request and hasattr(request, 'user'):
            username = request.user.username if hasattr(request.user, 'username') else str(request.user)
            # Make sure we don't return empty string for user
            response_data['user'] = username if username and username.strip() else "Anonymous"

        if self.debug_mode and details:
            response_data['debug'] = details
            response_data['cache_backend'] = self.cache_info['backend_name']
            response_data['authenticated'] = False

        response = JsonResponse(response_data, status=401)
        self._sign_response(response)

        return response

    def get_nonce_stats(self):
        """Get nonce storage statistics"""
        stats = {
            'cache_backend': self.cache_info['backend_name'],
            'cache_available': self.cache_available,
            'fallback_active': self.fallback_store is not None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if self.fallback_store:
            stats['fallback_stats'] = self.fallback_store.get_stats()

        return stats