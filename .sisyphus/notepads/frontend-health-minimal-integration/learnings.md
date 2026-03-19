Extracted INITIAL_MESSAGES, MOCK_TRACKS, and handleSendMessage mock logic to frontend/src/mock/ files. Behavior remains identical. 
Added frontend/src/config/api.ts and frontend/src/services/health.ts to handle backend health checks via /api/health proxy path. 
The health state lives in App.tsx as `systemStatus` and is passed to Sidebar.
