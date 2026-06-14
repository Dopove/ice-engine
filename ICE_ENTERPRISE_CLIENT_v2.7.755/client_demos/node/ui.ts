export class UI {
    static CYAN = '\x1b[96m';
    static GREEN = '\x1b[92m';
    static MAGENTA = '\x1b[95m';
    static YELLOW = '\x1b[93m';
    static BOLD = '\x1b[1m';
    static RESET = '\x1b[0m';

    static header(text: string) {
        console.log(`\n${this.BOLD}${this.CYAN}┌${'─'.repeat(text.length + 2)}┐${this.RESET}`);
        console.log(`${this.BOLD}${this.CYAN}│ ${text} │${this.RESET}`);
        console.log(`${this.BOLD}${this.CYAN}└${'─'.repeat(text.length + 2)}┘${this.RESET}\n`);
    }

    static system(text: string) {
        console.log(`${this.YELLOW}⚙️  [SYSTEM]:${this.RESET} ${text}`);
    }

    static user(text: string) {
        console.log(`${this.GREEN}👤 [USER]:${this.RESET} ${text}`);
    }

    static agent(text: string) {
        console.log(`${this.MAGENTA}🧊 [ICE AGENT]:${this.RESET} ${text}`);
    }

    static info(text: string) {
        console.log(`${this.YELLOW}💡 [INFO]:${this.RESET} ${text}`);
    }

    static param(name: string, value: string | number | boolean) {
        console.log(`  ${this.BOLD}${name}:${this.RESET} ${value}`);
    }

    static response(name: string, value: string) {
        console.log(`\n${this.BOLD}▶ ${name}:${this.RESET}\n${value}`);
    }

    static error(text: string) {
        console.error(`${this.BOLD}\n❌ [ERROR]:${this.RESET} ${text}\n`);
    }

    static success(text: string) {
        console.log(`\n${this.BOLD}${this.GREEN}✅ [VERDICT]: ${text}${this.RESET}\n`);
    }

    static step(text: string) {
        console.log(`\n${this.BOLD}▶ ${text}${this.RESET}`);
    }

    static async simulateProcessing(seconds = 1.5, message = "Processing") {
        const chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
        let i = 0;
        const endTime = Date.now() + seconds * 1000;
        
        while (Date.now() < endTime) {
            process.stdout.write(`\r${this.CYAN}${chars[i % chars.length]} ${message}...${this.RESET}`);
            await new Promise(r => setTimeout(r, 100));
            i++;
        }
        process.stdout.write(`\r${' '.repeat(message.length + 15)}\r`);
    }
}
