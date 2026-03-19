"Endpoint: /api/chat. Returns: session_id, assistant_text, recommendations, state (mood, scene, genre, preferred_energy, preferred_vocals)." 

- Added mappers to convert backend ChatState to SessionContext and recommendations to Track objects.
- mapChatStateToSessionContext: mood/scene/genre -> arrays, energy/vocal -> localized chips.
- mapRecommendationsToTracks: handles string IDs and object-based recommendations with deterministic placeholders.
- App chat flow now appends user message first, shows a temporary "正在思考..." agent bubble, then replaces it with backend `assistant_text` and mapped context/recommendations.
- On `/api/chat` failure, UI adds a Chinese fallback notice and reuses `getMockResponse(content)` to keep left context/right tracks responsive.
- Current `session_id` is displayed in the Sidebar's System Status area, wired from `App.tsx`.
