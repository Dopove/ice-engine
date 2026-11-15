# SPDX-License-Identifier: BSL-1.1

class CircuitBreakerOpen(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        redis_client=None,
        redis_ttl: int = 3600,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self._state = 0  # 0=closed, 1=open, 2=half_open
        self._redis = redis_client
        self._redis_ttl = redis_ttl
        self._redis_key = f"circuit_breaker:{name}"

        # Try to load persisted state
        if self._redis:
            self._load_state()

    def _load_state(self):
        """Load circuit breaker state from Redis."""
        try:
            import orjson
            data = self._redis.get(self._redis_key)
            if data:
                state = orjson.loads(data)
                self.failures = state.get("failures", 0)
                self.last_failure_time = state.get("last_failure_time", 0)
                self._state = state.get("state", 0)
                logger.info(f"CircuitBreaker {self.name}: Loaded state {self._state} from Redis")
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker state: {e}")

    def _save_state(self):
        """Persist circuit breaker state to Redis."""
        if not self._redis:
            return
        try:
            import orjson
            import time
            state = {
                "failures": self.failures,
                "last_failure_time": self.last_failure_time,
                "state": self._state,
                "updated_at": time.time(),
            }
            self._redis.setex(
                self._redis_key,
                self._redis_ttl,
                orjson.dumps(state)
            )
        except Exception as e:
            logger.warning(f"Failed to save circuit breaker state: {e}")

    def _update_metric(self):
        try:
            from ice.core.metrics import ICE_CIRCUIT_BREAKER_STATE
            ICE_CIRCUIT_BREAKER_STATE.labels(provider=self.name).set(self._state)
        except Exception:
            pass

    async def __aenter__(self):
        import time
        if self.failures >= self.failure_threshold:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self._state = 2  # half_open
                self._update_metric()
                self._save_state()
                return self
            else:
                self._state = 1  # open
                self._update_metric()
                self._save_state()
                raise CircuitBreakerOpen(f"Circuit {self.name} is open.")
        self._state = 0  # closed
        self._update_metric()
        self._save_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import time
        if exc_type is not None:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self._state = 1  # open
        else:
            self.failures = 0
            self._state = 0  # closed
        self._update_metric()
        self._save_state()
