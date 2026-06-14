import express, { Request, Response, NextFunction } from 'express';
import cookieParser from 'cookie-parser';
import jwt from 'jsonwebtoken';
import { IceClient } from '@dopove/ice-engine';

const app = express();
app.use(express.json());
app.use(cookieParser());

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

const SECRET = "enterprise-jwt-secret";

// Custom interface to extend Express Request with ICE session data
interface AuthenticatedRequest extends Request {
    iceUser?: string;
    iceThread?: string;
}

// 1. Session Middleware
// Extracts identity from JWT and thread context from a frontend cookie.
const sessionMiddleware = (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    const token = req.cookies.auth_token;
    const thread = req.cookies.active_thread_id || "default-browser-session";

    if (!token) return res.status(401).json({ error: "Unauthorized" });

    try {
        const decoded = jwt.verify(token, SECRET) as { sub: string };
        req.iceUser = decoded.sub;
        req.iceThread = thread;
        next();
    } catch (e) {
        res.status(401).json({ error: "Invalid Session Token" });
    }
};

/**
 * Secure Web App connectivity.
 * Ideal for Next.js/React applications where state is managed securely via cookies.
 */
app.post('/web/chat', sessionMiddleware, async (req: AuthenticatedRequest, res: Response) => {
    console.log(`[Cookie Session]: Validated ${req.iceUser} for thread ${req.iceThread}`);

    try {
        const response = await ice.chat.completions.create({
            model: "gpt-4o",
            messages: [{ role: "user", content: req.body.message }],
            sessionId: req.iceThread!,
            userId: req.iceUser!,
            maxTokens: 2000
        });

        res.json({ reply: response.choices[0].message.content });
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

// Helper for testing
app.get('/login', (req, res) => {
    const token = jwt.sign({ sub: "user-123" }, SECRET);
    res.cookie('auth_token', token, { httpOnly: true });
    res.cookie('active_thread_id', 'marketing-campaign-discussion');
    res.json({ message: "Cookies set. You can now hit /web/chat." });
});

app.listen(3002, () => console.log('JWT/Cookie Demo running on port 3002'));
