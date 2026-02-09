# replit.md

## Overview

This is a **J.A.R.V.I.S. AI Dashboard** — a real-time system monitoring dashboard with a futuristic cyber-grid aesthetic. It features an animated AI orb, system metrics gauges (CPU, memory, GPU/CPU temperature), a terminal log viewer, a focus window (code/docs/email viewer), and sidebar controls for toggling modes (gaming, mute mic, conversational). Data flows from the server to the client via WebSocket for live updates with simulated system metrics and log messages.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight client-side router)
- **State Management**: TanStack React Query for server state; React hooks for local state
- **Styling**: Tailwind CSS with CSS variables for theming; dark mode forced on by default
- **UI Components**: shadcn/ui (new-york style) built on Radix UI primitives, stored in `client/src/components/ui/`
- **Animations**: Framer Motion for transitions, orb effects, and gauge animations
- **Build Tool**: Vite with React plugin
- **Path Aliases**: `@/` maps to `client/src/`, `@shared/` maps to `shared/`

### Backend
- **Runtime**: Node.js with TypeScript (tsx for dev, esbuild for production)
- **Framework**: Express 5
- **WebSocket**: `ws` library on the same HTTP server for real-time dashboard data (simulated metrics, logs, state changes)
- **API Pattern**: REST endpoints under `/api/` plus WebSocket for live data streaming
- **Storage**: Currently uses in-memory storage (`MemStorage` class in `server/storage.ts`). The `IStorage` interface exists to swap in a database-backed implementation later.

### Database
- **ORM**: Drizzle ORM configured for PostgreSQL
- **Schema**: Defined in `shared/schema.ts` — currently just a `users` table with `id`, `username`, `password`
- **Validation**: Zod schemas generated from Drizzle schema via `drizzle-zod`
- **Migrations**: Drizzle Kit with `db:push` command; migrations output to `./migrations/`
- **Connection**: Requires `DATABASE_URL` environment variable (PostgreSQL)
- **Note**: The app currently uses in-memory storage and doesn't actively query the database, but the schema and Drizzle config are fully set up for PostgreSQL.

### Build & Deploy
- **Dev**: `npm run dev` runs tsx with Vite dev server middleware (HMR via `/vite-hmr`)
- **Build**: Custom build script (`script/build.ts`) — Vite builds the client to `dist/public/`, esbuild bundles the server to `dist/index.cjs`
- **Production**: `npm start` serves the built client as static files and runs the bundled server
- **Key bundled deps**: Express, Drizzle, ws, and other server deps are bundled to reduce cold start times

### Project Structure
```
client/           # Frontend React app
  src/
    components/   # Dashboard-specific components (ai-orb, gauges, terminal, etc.)
    components/ui/# shadcn/ui component library
    hooks/        # Custom hooks (useWebSocket, useToast, useMobile)
    lib/          # Utilities (queryClient, cn helper)
    pages/        # Page components (dashboard, not-found)
server/           # Backend Express server
  index.ts        # Entry point, middleware setup
  routes.ts       # API routes and WebSocket server setup
  storage.ts      # Storage interface and in-memory implementation
  vite.ts         # Vite dev server integration
  static.ts       # Production static file serving
shared/           # Shared between client and server
  schema.ts       # Drizzle database schema and Zod types
```

## External Dependencies

- **PostgreSQL**: Required database (connection via `DATABASE_URL` env var). Used with Drizzle ORM, though currently the app runs with in-memory storage.
- **WebSocket**: Native `ws` library for real-time communication between server and dashboard client. The server simulates system metrics, log entries, focus window content, and Jarvis state changes, pushing updates every few seconds.
- **Google Fonts**: Oxanium, Space Grotesk, JetBrains Mono, Fira Code, Geist Mono, DM Sans, Architects Daughter — loaded via external CDN links in `client/index.html`.
- **Replit Plugins**: `@replit/vite-plugin-runtime-error-modal`, `@replit/vite-plugin-cartographer`, `@replit/vite-plugin-dev-banner` — development-only Replit integration plugins.
- **No external AI/API services** are currently integrated despite the AI dashboard theme — all data is simulated server-side.