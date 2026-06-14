import express from 'express';
import chatRoutes from './routes/chatRoutes';

// ==============================================================================
// MAIN EXPRESS APPLICATION ENTRYPOINT
// ==============================================================================

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Health Check
app.get('/health', (req, res) => {
    res.json({ status: 'online', engine: 'ICE Thin Client Node.js v2.7.755' });
});

// Register the routes that utilize the ICE Singleton
app.use('/api/v1', chatRoutes);

app.listen(PORT, () => {
    console.log(`🚀 Starting Enterprise ICE Node.js API Example on http://localhost:${PORT}`);
    console.log(`   Ensure the primary ICE Python Engine is running at http://localhost:8008/v1`);
});
