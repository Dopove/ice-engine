#!/usr/bin/env node
import * as readline from 'readline';
import * as path from 'path';
import * as os from 'os';
import { IceClient } from '@dopove/ice-engine';

// ==============================================================================
// CLI AGENT CONFIGURATION (Node.js)
// ==============================================================================
// Initialize the Thin Client. It routes traffic through the central C++ Engine,
// ensuring the CLI tool stays lightweight and fast.

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "local-cli-bypass"
});

// Bind memory to the current directory to create "Project-Scoped Memory"
// If the user runs this CLI in /src/frontend, it remembers frontend context.
// If they run it in /src/backend, it remembers backend context.
const WORKSPACE_SESSION_ID = `cli-workspace-${process.cwd().replace(/[^a-zA-Z0-9]/g, '-')}`;
const USER_ID = process.env.USER || os.userInfo().username || "local-dev";

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: '❯ '
});

console.log(`🤖 ICE Node.js CLI Agent Initialized.`);
console.log(`📁 Workspace Memory Bound: ${WORKSPACE_SESSION_ID}`);
console.log(`Type 'exit' to quit.\n`);

rl.prompt();

rl.on('line', async (line) => {
    const input = line.trim();
    if (!input) {
        rl.prompt();
        return;
    }

    if (input.toLowerCase() === 'exit' || input.toLowerCase() === 'quit') {
        console.log('Goodbye!');
        process.exit(0);
    }

    try {
        process.stdout.write('⚙️  Thinking...\n🤖 ');

        // 1. Infinite Context Generation
        // The ICE C++ Bridge automatically fetches previous terminal history for this workspace
        // and injects it into the LLM context before making the request.
        const response = await ice.chat.completions.create({
            model: "gpt-4o", // The Engine handles upstream routing
            messages: [{ role: "user", content: input }],
            sessionId: WORKSPACE_SESSION_ID,
            userId: USER_ID,
            maxTokens: 4096
        });

        console.log(response.choices[0].message.content + '\n');
    } catch (error: any) {
        console.error(`\n❌ Error: ${error.message}\n`);
    }

    rl.prompt();
}).on('close', () => {
    console.log('\nGoodbye!');
    process.exit(0);
});
