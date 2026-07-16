class CircuitBreakerOpen(Exception):
    pass

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0

    async def __aenter__(self):
        import time
        if self.failures >= self.failure_threshold:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                # Try to recover
                return self
            else:
                raise CircuitBreakerOpen(f"Circuit {self.name} is open.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import time
        if exc_type is not None:
            self.failures += 1
            self.last_failure_time = time.time()
        else:
            self.failures = 0
