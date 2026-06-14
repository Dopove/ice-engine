import express, { Request, Response } from 'express';
import { IceClient, SessionManager } from '@dopove/ice-engine';

const app = express();
app.use(express.json());

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

/**
 * Standard Stateless HTTP connectivity.
 * ICE provides a built-in 'SessionManager' to automatically parse standard headers.
 */
app.post('/api/chat', async (req: Request, res: Response) => {
    // 1. Automatic Header Parsing
    // Expects 'x-session-id' and 'x-user-id' in req.headers
    const sessionContext = new SessionManager(req).getContext();

    // 2. Fallback protection
    if (!sessionContext.sessionId) {
        return res.status(400).json({ error: "Missing x-session-id header" });
    }

    console.log(`[HTTP Session]: Process request for ${sessionContext.userId} in thread ${sessionContext.sessionId}`);

    try {
        const response = await ice.chat.completions.create({
            model: "claude-3-5-sonnet",
            messages: [{ role: "user", content: req.body.message }],
            sessionId: sessionContext.sessionId,
            userId: sessionContext.userId,
            maxTokens: 2000
        });

        res.json({ reply: response.choices[0].message.content });
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

app.listen(3001, () => console.log('HTTP Session Demo running on port 3001'));
