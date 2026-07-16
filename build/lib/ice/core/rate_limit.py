import time
import asyncio

class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets = {}
        self.last_refill = {}
        self.lock = asyncio.Lock()

    async def consume(self, key: str, tokens: int = 1) -> bool:
        async with self.lock:
            now = time.time()
            if key not in self.buckets:
                self.buckets[key] = self.capacity
                self.last_refill[key] = now

            # Refill
            elapsed = now - self.last_refill[key]
            refill_amount = int(elapsed * self.refill_rate)
            if refill_amount > 0:
                self.buckets[key] = min(self.capacity, self.buckets[key] + refill_amount)
                self.last_refill[key] = now

            if self.buckets[key] >= tokens:
                self.buckets[key] -= tokens
                return True
            return False