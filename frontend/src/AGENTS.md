# AGENTS.md — Frontend Source
<!-- OMO_INTERNAL_INITIATOR -->

OVERVIEW
React 19 frontend for music recommendation agent using Zustand and Tailwind v4.

STRUCTURE
- components/: UI logic split into pages, layout, and auth.
- contexts/: Global providers like AudioPlayerContext.
- services/: API clients for chat, feedback, and sessions.
- store/: Zustand state management for auth, chat, and playlists.
- mappers/: Transforms API responses into frontend models.
- mock/: Static data for local development.
- types/: Centralized TypeScript interfaces.
- lib/: Shared utility functions.

WHERE TO LOOK
- Chat logic: components/pages/ChatPage.tsx and store/useChatStore.ts.
- Audio playback: contexts/AudioPlayerContext.tsx.
- API calls: services/api.ts.
- Data flow: mappers/ for backend to frontend conversion.

CONVENTIONS
- Use PascalCase for component files and names.
- Functional components with hooks only.
- 2 spaces indentation. Use semicolons.
- Strict TypeScript. Use Record<string, unknown> instead of any.
- Services must throw Error on HTTP or parsing failure.
- Tailwind v4 for all styling.
- API base is /api, proxied to localhost:8000.

ANTI-PATTERNS
- No class components.
- Avoid prop drilling. Use Zustand or Context.
- Don't use any.
- No inline styles. Use Tailwind.
- Don't bypass mappers for complex API data.
- Never repeat parent AGENTS.md content.
