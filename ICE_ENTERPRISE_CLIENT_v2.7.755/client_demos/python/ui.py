import sys
import time
import asyncio

class UI:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    MAGENTA = '\033[95m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    @classmethod
    def header(cls, text):
        print(f"\n{cls.BOLD}{cls.CYAN}┌{'─' * (len(text) + 2)}┐{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}│ {text} │{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}└{'─' * (len(text) + 2)}┘{cls.RESET}\n")

    @classmethod
    def system(cls, text):
        print(f"{cls.YELLOW}⚙️  [SYSTEM]:{cls.RESET} {text}")

    @classmethod
    def user(cls, text):
        print(f"{cls.GREEN}👤 [USER]:{cls.RESET} {text}")

    @classmethod
    def agent(cls, text):
        print(f"{cls.MAGENTA}🧊 [ICE AGENT]:{cls.RESET} {text}")

    @classmethod
    def success(cls, text):
        print(f"\n{cls.BOLD}{cls.GREEN}✅ [VERDICT]: {text}{cls.RESET}\n")

    @classmethod
    def param(cls, name, value):
        print(f"  {cls.BOLD}{name}:{cls.RESET} {value}")
        
    @classmethod
    def step(cls, text):
        print(f"\n{cls.BOLD}▶ {text}{cls.RESET}")
        
    @classmethod
    async def simulate_processing(cls, seconds=1.5, message="Processing"):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        end_time = time.time() + seconds
        i = 0
        while time.time() < end_time:
            sys.stdout.write(f"\r{cls.CYAN}{chars[i % len(chars)]} {message}...{cls.RESET}")
            sys.stdout.flush()
            await asyncio.sleep(0.1)
            i += 1
        sys.stdout.write(f"\r{' ' * (len(message) + 15)}\r")
        sys.stdout.flush()
