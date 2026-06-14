import { IceClient } from '@dopove/ice-node'; // Or @dopove/ice-node-unlimited

// ==============================================================================
// THE SINGLETON THIN-CLIENT PATTERN (STAFF-ENGINEER GRADE)
// ==============================================================================
// Centralize your ICE connection and routing strategies here. 
// This ensures all express routes communicate with the Python Engine securely via IPC.

console.log("[System]: Initializing Global ICE Node.js Engine Client...");

// Instantiate the single, global engine proxy.
const iceClient = new IceClient({
    // Security: The JWT required to unlock the native bindings.
    licenseJwt: process.env.ICE_LICENSE_JWT || "dummy-for-unlimited-test",
    
    // Enterprise Enforcement: Apply strict Data Masking to all outbound requests
    defaultHeaders: {
        "X-Ice-Privacy-Masking": "strict",
        "X-Ice-Routing-Strategy": "sovereign-local"
    }
});

// Export the singleton instance for use across all controllers/routes
export default iceClient;
