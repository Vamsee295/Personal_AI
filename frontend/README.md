# Ultron – Frontend

The frontend of Ultron is a modern, responsive, and aesthetic user interface built with **Next.js** and **React**. It serves as the primary workspace for the AI-powered IDE experience.

## Core Roles
- **IDE Interface**: Provides a file explorer, multi-tab editor view (integration-ready), and integrated terminal.
- **AI Interaction**: Features a floating AI bubble and a dedicated chat side-panel for real-time communication with local LLMs.
- **System Control**: UI for triggering system-level actions like screen capture, voice assistant, and directory organisation.
- **Real-time Updates**: Uses WebSockets to stream AI responses and terminal outputs for a premium user experience.

## Technology Stack
- **Next.js / React**: Core UI framework.
- **Vanilla CSS**: Premium, custom-tailored styling with modern aesthetics (dark mode, glassmorphism).
- **Lucide React**: For sleek, consistent iconography.
- **Framer Motion**: For smooth micro-animations and transitions.

## Getting Started

### Prerequisites
1. **Node.js 18+** installed on your system.
2. **NPM** or **Yarn** package manager.

### Installation
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

### Running the Frontend
1. **Start the Development Server**:
   ```bash
   npm run dev
   ```
   The frontend will be accessible at `http://localhost:3000`.

## Architecture Note
The frontend communicates exclusively with the **Ultron Backend** via REST APIs and WebSockets. Ensure the backend is running at `http://localhost:8000` for the AI and system features to function correctly.
