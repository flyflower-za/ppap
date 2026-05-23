# PPAP File Verification Platform - Frontend

Vue 3 + TypeScript + Element Plus frontend for the file verification platform.

## Tech Stack

- **Framework**: Vue 3.4 (Composition API)
- **Language**: TypeScript 5.3
- **Build Tool**: Vite 5.0
- **UI Library**: Element Plus 2.5
- **State Management**: Pinia 2.1
- **Router**: Vue Router 4.2
- **HTTP Client**: Axios 1.6
- **PDF Viewer**: PDF.js 4.0

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API client modules
│   ├── assets/        # Static assets
│   ├── components/    # Reusable components
│   ├── layouts/       # Page layouts
│   ├── router/        # Vue Router config
│   ├── stores/        # Pinia stores
│   ├── styles/        # Global styles
│   ├── types/         # TypeScript types
│   ├── views/         # Page components
│   ├── App.vue        # Root component
│   └── main.ts        # Entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Quick Start

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment

```bash
# Create .env.local
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
```

### 3. Start dev server

```bash
npm run dev
```

### 4. Build for production

```bash
npm run build
```

### 5. Preview production build

```bash
npm run preview
```

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| /login | LoginPage | User login |
| /tasks | TaskCenterPage | Upload & task list |
| /history | HistoryPage | File history with filters |
| /files/:id | FileDetailPage | File verification details |
| /notifications | NotificationsPage | Notification center |
| /settings | SettingsPage | User settings |

## Development

### Code formatting

```bash
npm run lint
```
