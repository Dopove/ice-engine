export interface EnterpriseTunables {
    memoryCapGb?: number;
    maxStitchConcurrency?: number;
    retentionDays?: number;
    chunkSize?: number;
    maxInputTokens?: number;
    chunkOverlap?: number;
    maxContinuations?: number;
    priorityMemoryLimit?: number;
    reasoningRecallLimit?: number;
    llmRoutingStrategy?: "sovereign-local" | "cloud-fallback";
    privacyMasking?: "strict" | "none";
}

export interface IceClientConfig {
    baseURL?: string;
    licenseJwt: string;
    defaultHeaders?: Record<string, string>;
    enterpriseTunables?: EnterpriseTunables;
}

export interface ChatMessage {
    role: "system" | "user" | "assistant" | "tool";
    content: string | any[];
    name?: string;
}

export interface ChatCompletionRequest {
    model: string;
    messages: ChatMessage[];
    sessionId: string;
    userId?: string;
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
    tools?: any[];
    toolChoice?: any;
    responseFormat?: any;
}
