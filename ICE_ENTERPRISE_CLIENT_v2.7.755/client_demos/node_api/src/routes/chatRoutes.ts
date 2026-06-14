import { Router, Request, Response } from 'express';
import { SessionManager } from '@dopove/ice-node';

// 1. Import the globally configured Singleton client!
import iceClient from '../core/iceConfig';

const router = Router();

/**
 * POST /api/v1/chat
 * Handles an infinite memory chat request using the Python Engine IPC Bridge.
 */
router.post('/chat', async (req: Request, res: Response) => {
    try {
        const { message, model = "claude-3-5-sonnet" } = req.body;

        // 2. Session extraction: 
        // ICE handles finding 'x-session-id' and user context from the Express headers.
        const session = new SessionManager(req).getContext();

        if (!message) {
            return res.status(400).json({ error: "Message is required." });
        }

        console.log(`[Route]: Processing chat for User: ${session.userId}, Session: ${session.sessionId}`);

        // 3. Inference with Infinite Memory
        // The thin client securely bridges the request to the ICE core.
        // It handles ContextPager injection automatically.
        const response = await iceClient.chat.completions.create({
            model: model,
            messages: [{ role: "user", content: message }],
            sessionId: session.sessionId,
            userId: session.userId,
            maxTokens: 4096
        });

        res.json({
            status: "success",
            reply: response.choices[0].message.content,
            sessionId: session.sessionId
        });

    } catch (error: any) {
        console.error("[Route Error]:", error.message);
        res.status(500).json({ error: "Internal Server Error during ICE Inference." });
    }
});

export default router;
