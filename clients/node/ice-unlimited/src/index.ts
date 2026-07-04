// The only purpose of this file is to load the C++ binary and expose its functions.
const bridge = require("../build/Release/ice_bridge.node");
import { spawnSync } from 'child_process';
import * as path from 'path';

export * from './interfaces';

/**
 * @dopove/ice-node-unlimited (v2.7.756)
 * Unlimited Node.js Native Client for the Infinite Context Engine.
 * Operates as a stateless native layer via high-speed IPC.
 */
export class IceClient {
    private apiKey: string;
    private sdkParams: any;
    private env: any;

    constructor(config: import('./interfaces').IceClientConfig = {}) {
        this.apiKey = config.apiKey || "ice-unlimited-key";
        
        // Prepare the environment for the Python bridge
        this.env = { ...process.env, ICE_LICENSE_JWT: this.apiKey, ICE_ALLOW_DEFAULT_KEY: "1" } as { [key: string]: string | undefined };
        
        // Prepare the base SDK init params
        this.sdkParams = { license_key: this.apiKey };

        if (config.enterpriseTunables) {
            const tunables = config.enterpriseTunables;
            // Pass tunables as env vars to the embedded engine
             if (tunables.memoryCapGb) this.env["ICE_MEMORY_CAP_GB"] = tunables.memoryCapGb.toString();
             if (tunables.maxStitchConcurrency) this.env["ICE_MAX_STITCH_CONCURRENCY"] = tunables.maxStitchConcurrency.toString();
             if (tunables.retentionDays) this.env["ICE_RETENTION_DAYS"] = tunables.retentionDays.toString();
             if (tunables.chunkSize) this.env["ICE_CHUNK_SIZE"] = tunables.chunkSize.toString();
             if (tunables.maxInputTokens) this.env["ICE_POST_COMPRESSION_LIMIT"] = tunables.maxInputTokens.toString();
             if (tunables.chunkOverlap) this.env["ICE_CHUNK_OVERLAP"] = tunables.chunkOverlap.toString();
             if (tunables.maxContinuations) this.env["ICE_MAX_CONTINUATIONS"] = tunables.maxContinuations.toString();
             if (tunables.priorityMemoryLimit) this.env["ICE_PRE_COMPRESSION_LIMIT"] = tunables.priorityMemoryLimit.toString();
             if (tunables.reasoningRecallLimit) this.env["ICE_REASONING_RECALL_LIMIT"] = tunables.reasoningRecallLimit.toString();
             if (tunables.llmRoutingStrategy) this.env["ICE_LLM_ROUTING_STRATEGY"] = tunables.llmRoutingStrategy;
             if (tunables.privacyMasking) this.env["ICE_PRIVACY_MASKING"] = tunables.privacyMasking;
        }
    }

    public get chat() {
        const createCompletion = async (request: import('./interfaces').ChatCompletionRequest) => {
            const completion_params = {
                model: request.model,
                messages: request.messages,
                x_session_id: request.sessionId,
                x_user_id: request.userId || "anonymous",
                temperature: request.temperature || 0.7,
                max_tokens: request.maxTokens || 4096,
                stream: false, // IPC bridge does not support streaming
                tools: request.tools,
                tool_choice: request.toolChoice,
                response_format: request.responseFormat
            };
            
            const payload = JSON.stringify({
                sdk_params: this.sdkParams,
                completion_params: completion_params
            });

            // Locate the Python bridge script relative to this file
            const bridgeScriptPath = path.resolve(__dirname, '../../../../ice/node_bridge.py');
            
            // Execute the Python bridge script synchronously via IPC
            const result = spawnSync('python3', ['-c', 'import ice.node_bridge; import asyncio; asyncio.run(ice.node_bridge.main())'], {
                input: payload,
                env: this.env,
                encoding: 'utf-8',
                maxBuffer: 1024 * 1024 * 50 // 50 MB buffer for large responses
            });

            if (result.status !== 0) {
                try {
                    const err = JSON.parse(result.stderr);
                    throw new Error(`[ICE Python Bridge Error] ${err.error.type}: ${err.error.message}`);
                } catch {
                     throw new Error(`[ICE Python Bridge Error] An unknown error occurred. Stderr: ${result.stderr}`);
                }
            }

            try {
                return JSON.parse(result.stdout);
            } catch (e) {
                 throw new Error(`[ICE Node.js Error] Failed to parse JSON response from Python bridge: ${e}. Raw output: ${result.stdout}`);
            }
        };

        return { completions: { create: createCompletion } };
    }
}

export class SessionManager {
    private userId: string = "anonymous";
    private sessionId: string;

    constructor(request: any) {
        if (request.user?.id) this.userId = String(request.user.id);
        else if (request.state?.userId) this.userId = String(request.state.userId);

        this.sessionId = request.headers?.["x-session-id"] || 
                         request.session?.ice_session_id || 
                         `sess_${Math.random().toString(36).substring(2, 14)}`;

        if (request.session && !request.session.ice_session_id) {
            request.session.ice_session_id = this.sessionId;
        }
    }

    public getContext() {
        return { userId: this.userId, sessionId: this.sessionId };
    }
}
