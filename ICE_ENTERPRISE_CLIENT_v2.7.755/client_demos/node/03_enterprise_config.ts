import { IceClient } from '@dopove/ice-engine';
import { UI } from './ui'; // Assuming a UI helper for cleaner output

async function runCustomizationDemo() {
    UI.header("ICE Node.js: Enterprise Customization & Compliance Demo");

    // --- Define all Enterprise Tunables ---
    const customTunables = {
        memoryCapGb: 64.0,
        maxStitchConcurrency: 50,
        retentionDays: 365,
        chunkSize: 12000,
        maxInputTokens: 128000,
        chunkOverlap: 1000,
        maxContinuations: 100,
        priorityMemoryLimit: 5,
        reasoningRecallLimit: 10,
        privacyMasking: "strict",
        llmRoutingStrategy: "sovereign-local",
        dynamicOutputBudget: false, // Explicitly disable for this demo
        defaultOutputTokens: 512, // Custom default output
    };

    let ice: IceClient;
    // Frictionless DX: Mock if no upstream key
    if (!process.env.OPENAI_API_KEY) {
        UI.info("API keys not found. Running in MOCK Mode for demonstration.");
        // Mock the IceClient and its chat.completions.create method
        ice = {
            chat: {
                completions: {
                    create: async (request: any) => ({
                        choices: [{ message: { content: "Mocked response based on custom tunables." } }]
                    })
                }
            },
            // Mock the config property to reflect the tunables
            config: { enterpriseTunables: customTunables }
        } as unknown as IceClient; // Cast to IceClient to satisfy type checker
    } else {
        UI.info("Booting live ICE Kernel connection...");
        // Initialize the client with all custom tunables
        ice = new IceClient({
            licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTc0MTEsICJleHAiOiAxODA5MzMzNDExLCAic3ViIjogInNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSJ9.mpTuzA3OLLNo3LOyY1jUTiFiMsoPm7eyIu8wA9hovzVdUyZNciga6i91Lmy-ipNqA6FDcB5KU6PIVVz7Uz8NVSprlddLqCQgEEZEGJ-PUGYVRt4idvaCms9X2bFeCSS-goZWi03Hd8FQn73YVjQ-no1gYisN26fZGsbqZuGfqsxy3uw2vMYALuXCk_EOY8kETABbnqasjSnGMzo_VKG7XS5xv25tBR8OkEpQObNLuciIXj6j54REntBodOi3H7CZwuE-zs6BtatqFi1UiCPYjbfzEdg1KVgdZMHIfS5WMwE-oPza0xU1CMMYapaHoBsrBSv5ncWstf4U24Xf-aNV_A",
            enterpriseTunables: customTunables
        });
    }

    UI.info("ICE Client initialized with Staff-Engineer compliance overrides.");
    UI.info("The following runtime boundaries have been programmatically applied to the kernel:");

    const currentConfig = ice.config.enterpriseTunables || {}; // Get tunables from the client's config

    UI.param("Memory Guardian Cap", `${currentConfig.memoryCapGb} GB`);
    UI.param("Max Stitch Concurrency", `${currentConfig.maxStitchConcurrency}`);
    UI.param("Ledger Retention", `${currentConfig.retentionDays} Days`);
    UI.param("Chunking Physics", `${currentConfig.chunkSize} chars/segment`);
    UI.param("Chunk Overlap", `${currentConfig.chunkOverlap} chars`);
    UI.param("Max Input Tokens", `${currentConfig.maxInputTokens}`);
    UI.param("Max Continuations", `${currentConfig.maxContinuations} turns`);
    UI.param("Priority Memory Limit", `${currentConfig.priorityMemoryLimit} items`);
    UI.param("Reasoning Recall Limit", `${currentConfig.reasoningRecallLimit} items`);
    UI.param("Privacy Masking", `${currentConfig.privacyMasking}`);
    UI.param("Routing Strategy", `${currentConfig.llmRoutingStrategy}`);
    // Assuming Dynamic Output Budget and Default Output Tokens are also part of enterpriseTunables
    UI.param("Dynamic Output Budget", `${currentConfig.dynamicOutputBudget}`);
    UI.param("Default Output Tokens", `${currentConfig.defaultOutputTokens}`);

    UI.info("The underlying PostgreSQL Ledger and ContextPager will now strictly adhere to these policies.");

    // Optional: Make a test call to show it's working
    try {
        const response = await ice.chat.completions.create({
            model: "llama3",
            messages: [{ role: "user", content: "Ping with custom tunables." }],
            sessionId: "config-test-01",
            userId: "admin-user"
        });
        UI.response("Test Chat Response", response.choices[0].message.content);
    } catch (e: any) {
        UI.error(`Test Chat Error: ${e.message}`);
    }
}

runCustomizationDemo().catch(console.error);
