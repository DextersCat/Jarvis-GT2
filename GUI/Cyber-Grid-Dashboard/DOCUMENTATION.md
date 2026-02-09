# J.A.R.V.I.S. AI Dashboard

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Tech Stack](#tech-stack)
5. [Getting Started](#getting-started)
6. [Deployment Guide](#deployment-guide)
7. [Configuration](#configuration)
8. [WebSocket Protocol](#websocket-protocol)
9. [Extending the Dashboard](#extending-the-dashboard)

---

## Overview

J.A.R.V.I.S. AI Dashboard is a single-page, real-time system monitoring dashboard with a futuristic cyber-grid aesthetic. It streams live data via WebSocket and presents system metrics, AI state, logs, and a mood/pain tracker in an immersive dark interface optimized for 1560x1440 displays.

All system data is currently simulated server-side. The WebSocket server can be replaced with a real data source (e.g., a Python monitoring agent) by matching the message protocol described below.

---

## Features

### Animated AI Orb
- Central visual element showing the AI assistant's current state
- Three modes: **Speaking** (blue pulse), **Listening** (cyan ripple), **Idle** (purple breathe)
- Animated voice waveform bars that respond to the current mode
- Radial glow effects and smooth state transitions via Framer Motion

### System Metrics Gauges
- Four circular SVG gauges displaying real-time values:
  - **CPU Usage** (0-100%) - blue theme
  - **Memory Usage** (0-100%) - cyan theme
  - **GPU Temperature** (0-100 C) - orange theme
  - **CPU Temperature** (0-100 C) - red theme
- Animated stroke-dashoffset transitions for smooth value changes
- Color-coded warning states (green/yellow/red based on thresholds)

### Glassmorphism Sidebar Controls
- Toggle switches with frosted-glass styling:
  - **Gaming Mode** - low latency priority
  - **Mute Mic** - microphone control
  - **Conversational Mode** - natural dialogue toggle
- Animated glow borders that respond to toggle state
- State changes are sent to the server via WebSocket

### Focus Window
- Multi-purpose content viewer with three modes:
  - **Code Editor** - syntax-highlighted code with line numbers (Python keywords, strings, numbers, comments)
  - **Google Docs** - document viewer with prose formatting
  - **Email Client** - email message display
- Expand/collapse to fullscreen
- Traffic light window controls (red/yellow/green dots)
- Content rotates automatically every 15 seconds via WebSocket

### System Log (Terminal)
- Scrolling terminal-style log feed showing the 8 most recent entries
- Color-coded severity levels: INFO (slate), WARN (amber), ERROR (red), SUCCESS (emerald)
- Timestamps and severity badges for each entry
- Auto-scrolls to latest entry
- 12px monospace font for readability

### Mood / Pain Tracker
- Quick-log widget for tracking personal wellness:
  - **Pain Level** - 5-point scale: None, Mild, Moderate, Severe, Extreme
  - **Anxiety Level** - 5-point scale: Calm, Slight, Moderate, High, Intense
- Visual level selector with color-coded fill (rose for pain, purple for anxiety)
- Log Entry button to save timestamped records
- Recent entries display showing last 3 logs with timestamps and values
- Data stored in browser session (client-side state)

### Dashboard Header
- Real-time digital clock (HH:MM:SS format) with date display
- Network status indicator (5G/4G/3G) with animated signal bars
- Encryption badge (AES-256) with shield icon and glow effect
- Connection status dot (green = online)

### Visual Design
- Dark cyber-grid background with subtle blue grid lines
- Radial gradient ambient lighting (blue, cyan, purple)
- Glassmorphism panels with backdrop blur throughout
- Oxanium and Space Grotesk fonts for a futuristic feel
- JetBrains Mono for all monospaced/terminal text
- Framer Motion animations on all component entries and transitions

---

## Project Structure

```
jarvis-dashboard/
  client/                     # Frontend React application
    src/
      components/
        ai-orb.tsx            # Animated AI orb with voice waveform
        circular-gauge.tsx    # Reusable circular SVG gauge
        dashboard-header.tsx  # Top bar with clock, status indicators
        focus-window.tsx      # Code/docs/email content viewer
        mood-tracker.tsx      # Pain and anxiety level tracker
        sidebar-controls.tsx  # Gaming, mic, conversation toggles
        system-gauges.tsx     # 4-gauge metrics grid
        terminal-log.tsx      # Scrolling system log feed
        ui/                   # shadcn/ui component library (Button, Switch, etc.)
      hooks/
        use-mobile.tsx        # Mobile detection hook
        use-toast.ts          # Toast notification hook
        use-websocket.ts      # WebSocket connection and data management
      lib/
        queryClient.ts        # TanStack Query client setup
        utils.ts              # Utility functions (cn helper)
      pages/
        dashboard.tsx         # Main dashboard page layout
        not-found.tsx         # 404 page
      App.tsx                 # Root app component with routing
      index.css               # Tailwind CSS with custom theme variables
      main.tsx                # React entry point
    index.html                # HTML template with Google Fonts

  server/                     # Backend Express server
    index.ts                  # Server entry point, middleware setup
    routes.ts                 # API routes + WebSocket server with simulated data
    storage.ts                # Storage interface (in-memory implementation)
    vite.ts                   # Vite dev server integration
    static.ts                 # Production static file serving

  shared/                     # Shared between client and server
    schema.ts                 # Drizzle database schema and Zod types

  script/
    build.ts                  # Production build script (Vite + esbuild)

  package.json                # Dependencies and scripts
  tsconfig.json               # TypeScript configuration
  tailwind.config.ts          # Tailwind CSS configuration
  vite.config.ts              # Vite build configuration
  drizzle.config.ts           # Drizzle ORM configuration
```

---

## Tech Stack

| Layer     | Technology                                      |
|-----------|--------------------------------------------------|
| Frontend  | React 18, TypeScript, Vite                       |
| Styling   | Tailwind CSS, CSS custom properties              |
| Animation | Framer Motion                                    |
| UI Kit    | shadcn/ui (Radix UI primitives)                  |
| Routing   | Wouter                                           |
| State     | TanStack React Query, React hooks                |
| Backend   | Node.js, Express 5, TypeScript                   |
| WebSocket | ws library                                       |
| ORM       | Drizzle ORM (PostgreSQL, configured but optional)|
| Fonts     | Oxanium, Space Grotesk, JetBrains Mono           |

---

## Getting Started

### Prerequisites
- Node.js 18 or later
- npm (comes with Node.js)

### Install Dependencies

```bash
npm install
```

### Run in Development Mode

```bash
npm run dev
```

This starts the Express server with Vite dev middleware. The app will be available at `http://localhost:5000`.

- Frontend hot-reloads via Vite HMR
- Backend restarts on file changes via tsx
- WebSocket streams simulated data immediately on connection

### Type Checking

```bash
npm run check
```

---

## Deployment Guide

### Option 1: Build and Run Locally

1. **Build the production bundle:**

```bash
npm run build
```

This runs the custom build script that:
- Builds the React frontend with Vite into `dist/public/`
- Bundles the Express server with esbuild into `dist/index.cjs`

2. **Start the production server:**

```bash
npm start
```

The server serves the built frontend as static files and runs on port 5000.

### Option 2: Deploy to Any Node.js Host

The built output in `dist/` is self-contained:

- `dist/index.cjs` - The complete server bundle (single file)
- `dist/public/` - Static frontend assets

**Steps for any hosting platform (Railway, Render, Fly.io, VPS, etc.):**

1. Build the project: `npm run build`
2. Copy the `dist/` folder to your server
3. Install Node.js 18+ on the server
4. Run `node dist/index.cjs`
5. Set the `PORT` environment variable if the host requires a specific port (defaults to 5000)

**Environment variables for deployment:**

| Variable       | Required | Description                                           |
|----------------|----------|-------------------------------------------------------|
| `PORT`         | No       | Server port (default: 5000)                           |
| `NODE_ENV`     | No       | Set to `production` for optimized serving             |
| `DATABASE_URL` | No       | PostgreSQL connection string (only if using database)  |
| `SESSION_SECRET`| No      | Session encryption key (only if using sessions)       |

### Option 3: Deploy with Docker

Create a `Dockerfile` in the project root:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
EXPOSE 5000
ENV NODE_ENV=production
CMD ["node", "dist/index.cjs"]
```

Build and run:

```bash
docker build -t jarvis-dashboard .
docker run -p 5000:5000 jarvis-dashboard
```

### Option 4: Deploy on Replit

The project is already configured for Replit deployment. Click the "Publish" button in the Replit workspace to make it live with a public URL.

### Post-Deployment Verification

After deploying, verify the dashboard is working:

1. Open the deployed URL in a browser
2. Confirm the dashboard loads with the cyber-grid background
3. Check that the clock updates in real time
4. Verify system gauges are animating with changing values
5. Confirm log entries appear in the terminal
6. Test the Mood/Pain Tracker by selecting levels and clicking Log Entry

---

## Configuration

### Fonts
External fonts are loaded via Google Fonts CDN in `client/index.html`. If deploying offline, download the fonts and update the link tags to point to local files.

### Theme Colors
All theme colors are defined as CSS custom properties in `client/src/index.css`. The dashboard uses a forced dark mode with:
- Background: deep navy (220 20% 6%)
- Primary: blue (210 100% 50%)
- Accent: purple (260 70% 55%)
- Destructive: red (0 70% 50%)

### Layout
The dashboard is optimized for 1560x1440 but responds to other screen sizes. Key layout values:
- Sidebar width: 300px
- Gauge diameter: 120px SVG
- Terminal: 8 visible lines
- Mood tracker: 320px wide

---

## WebSocket Protocol

The server sends JSON messages over WebSocket at `ws://<host>/ws`. Each message has a `type` field:

### Message Types

**`metrics`** - System resource data (every 500ms)
```json
{
  "type": "metrics",
  "data": {
    "cpu": 45,
    "memory": 62,
    "gpuTemp": 71,
    "cpuTemp": 58
  }
}
```

**`log`** - System log entry (every 2s)
```json
{
  "type": "log",
  "data": {
    "id": "log_1707500000000",
    "timestamp": "14:30:00",
    "level": "info",
    "message": "Neural network inference completed"
  }
}
```

**`state`** - AI state change (every 4s)
```json
{
  "type": "state",
  "data": {
    "mode": "speaking",
    "gamingMode": false,
    "muteMic": false,
    "conversationalMode": true
  }
}
```

**`focus`** - Focus window content (every 15s)
```json
{
  "type": "focus",
  "data": {
    "type": "code",
    "title": "neural_engine.py",
    "content": "import torch..."
  }
}
```

**`full`** - Full state snapshot (sent on initial connection)

### Client-to-Server Commands

```json
{
  "type": "command",
  "action": "toggle",
  "payload": {
    "key": "gamingMode",
    "value": true
  }
}
```

### Replacing with Real Data

To connect a real monitoring agent, implement a WebSocket client that sends messages in the format above to the same `/ws` endpoint, or modify `server/routes.ts` to replace the simulated intervals with real data sources.

---

## Extending the Dashboard

### Adding a New Widget

1. Create a new component in `client/src/components/`
2. Follow the existing glassmorphism pattern:
   ```tsx
   <motion.div
     style={{
       background: "rgba(5,8,18,0.8)",
       backdropFilter: "blur(16px)",
       border: "1px solid rgba(148,163,184,0.06)",
     }}
   >
   ```
3. Import and place it in `client/src/pages/dashboard.tsx`
4. If it needs live data, add a new message type to the WebSocket protocol in `server/routes.ts` and handle it in `client/src/hooks/use-websocket.ts`

### Adding a New Metric Gauge

1. Use the existing `CircularGauge` component from `client/src/components/circular-gauge.tsx`
2. Add the new metric field to the `SystemMetrics` interface in `use-websocket.ts`
3. Update the server simulation in `server/routes.ts` to include the new value
4. Place a new `<CircularGauge>` in `system-gauges.tsx`
