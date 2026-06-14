import { spawn } from 'child_process';
import * as path from 'path';

export * from './interfaces';

/**
 * @dopove/ice-node (v2.7.756)
 * Enterprise-grade Node.js Native Client for the Infinite Context Engine.
 * Operates as a stateless native layer via high-speed IPC.
 */
export class IceClient {
    private licenseJwt: string;
    private sdkParams: any;
    private env: any;

    constructor(config: import('./interfaces').IceClientConfig) {
        if (!config.licenseJwt) {
            throw new Error("❌ [ICE SECURITY] Enterprise Initialization Failed: Missing 'licenseJwt'.");
        }
        this.licenseJwt = config.licenseJwt;
        
        // Prepare the environment for the Python bridge
        this.env = { ...process.env, ICE_LICENSE_JWT: this.licenseJwt } as { [key: string]: string | undefined };
        
        // Prepare the base SDK init params
        this.sdkParams = { license_key: this.licenseJwt };

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
        const createCompletion = async (request: import('./interfaces').ChatCompletionRequest): Promise<any> => {
            
            const completion_params = {
                model: request.model,
                messages: request.messages,
                x_session_id: request.sessionId,
                x_user_id: request.userId || "anonymous",
                temperature: request.temperature || 0.7,
                max_tokens: request.maxTokens || 4096,
                stream: !!request.stream,
                tools: request.tools,
                tool_choice: request.toolChoice,
                response_format: request.responseFormat
            };
            
            const payload = JSON.stringify({
                sdk_params: this.sdkParams,
                completion_params: completion_params
            });

            // The Node.js SDK requires that the 'ice-engine' Python package is installed.
            const pythonExecutable = process.env.ICE_PYTHON_EXECUTABLE || 'python3';

            if (!request.stream) {
                return new Promise((resolve, reject) => {
                    const child = spawn(pythonExecutable, ['-c', 'import ice.node_bridge; import asyncio; asyncio.run(ice.node_bridge.main())'], {
                        env: this.env
                    });
                    
                    let stdoutData = '';
                    let stderrData = '';
                    
                    child.stdout.on('data', (data) => { stdoutData += data.toString(); });
                    child.stderr.on('data', (data) => { stderrData += data.toString(); });
                    
                    child.on('close', (code) => {
                        if (code !== 0) {
                            try {
                                const err = JSON.parse(stderrData);
                                reject(new Error(`[ICE Python Bridge Error] ${err.error.type}: ${err.error.message}`));
                            } catch {
                                reject(new Error(`[ICE Python Bridge Error] An unknown error occurred. Stderr: ${stderrData}`));
                            }
                        } else {
                            try {
                                resolve(JSON.parse(stdoutData));
                            } catch (e) {
                                reject(new Error(`[ICE Node.js Error] Failed to parse JSON response from Python bridge: ${e}. Raw output: ${stdoutData}`));
                            }
                        }
                    });
                    
                    child.on('error', (err) => {
                        reject(new Error(`[ICE Python Bridge Execution Error] Failed to start Python process. Ensure 'python3' is in your PATH and the 'ice-engine' wheel is installed. Error: ${err.message}`));
                    });
                    
                    child.stdin.write(payload);
                    child.stdin.end();
                });
            } else {
                const env = this.env;
                async function* streamGenerator() {
                    let errorReject: ((err: any) => void) | null = null;
                    const errorPromise = new Promise((_, reject) => { errorReject = reject; });
                    const child = spawn(pythonExecutable, ['-c', 'import ice.node_bridge; import asyncio; asyncio.run(ice.node_bridge.main())'], {
                        env: env
                    });

                    let buffer = '';
                    let stderrData = '';
                    const queue: string[] = [];
                    let waitNext: (() => void) | null = null;
                    let isClosed = false;

                    child.stdout.on('data', (data) => {
                        buffer += data.toString();
                        let parts = buffer.split('\\n\\n');
                        buffer = parts.pop() || '';
                        for (const part of parts) {
                            if (part.startsWith('data: ')) {
                                const dataStr = part.substring(6);
                                if (dataStr === '[DONE]') {
                                    isClosed = true;
                                } else {
                                    queue.push(dataStr);
                                }
                                if (waitNext) {
                                    waitNext();
                                    waitNext = null;
                                }
                            }
                        }
                    });

                    child.stderr.on('data', (data) => { stderrData += data.toString(); });

                    child.on('close', (code) => {
                        isClosed = true;
                        if (code !== 0) {
                            try {
                                const err = JSON.parse(stderrData);
                                if (errorReject) errorReject(new Error(`[ICE Python Bridge Error] ${err.error.type}: ${err.error.message}`));
                            } catch {
                                if (errorReject) errorReject(new Error(`[ICE Python Bridge Error] An unknown error occurred. Stderr: ${stderrData}`));
                            }
                        }
                        if (waitNext) { waitNext(); waitNext = null; }
                    });

                    child.on('error', (err) => {
                        isClosed = true;
                        if (errorReject) errorReject(new Error(`[ICE Python Bridge Execution Error] Failed to start Python process. Error: ${err.message}`));
                        if (waitNext) { waitNext(); waitNext = null; }
                    });

                    child.stdin.write(payload);
                    child.stdin.end();

                    while (true) {
                        if (queue.length > 0) {
                            const dataStr = queue.shift();
                            try {
                                yield JSON.parse(dataStr!);
                            } catch (e) {
                                yield dataStr; // yield raw string if unparseable
                            }
                        } else if (isClosed) {
                            break;
                        } else {
                            await Promise.race([
                                new Promise<void>(resolve => { waitNext = resolve; }),
                                errorPromise
                            ]);
                        }
                    }
                }
                return streamGenerator();
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