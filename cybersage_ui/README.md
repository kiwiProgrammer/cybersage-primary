# CyberSage UI

A React-based dashboard for monitoring and managing the CyberSage CTI processing pipeline.

## Features

- **Task Submission**: Submit CTI URLs for processing through Agent A
- **Real-time Monitoring**: Track task progress across all agents
- **Task Flow Visualization**: Visual representation of the pipeline flow (Agent A → Agent B → Agent C)
- **Task Management**: View and filter tasks by status
- **Auto-refresh**: Automatic polling for task updates

## Architecture

The dashboard interacts with three main services:

1. **Agent A Web** (port 8090): CTI URL processing
2. **Agent B Web** (port 8200): JSON transformation and Qdrant ingestion
3. **Agent C Queue** (port 8300): Vulnerability analysis queue

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The app will be available at http://localhost:3000

### Environment Variables

Create a `.env.local` file for local development:

```bash
REACT_APP_AGENT_A_URL=http://localhost:8090
REACT_APP_AGENT_B_URL=http://localhost:8200
REACT_APP_AGENT_C_QUEUE_URL=http://localhost:8300
```

## Docker

### Build

```bash
docker build -t cybersage-ui .
```

### Run

```bash
docker run -p 3000:80 cybersage-ui
```

## Docker Compose

The UI is included in the main docker-compose.yml:

```bash
docker-compose up cybersage_ui
```

Access the dashboard at http://localhost:3000

## Project Structure

```
cybersage_ui/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   │   ├── TaskSubmitForm.tsx
│   │   ├── TaskFlowVisualization.tsx
│   │   └── AllTasksList.tsx
│   ├── api.ts          # API service layer
│   ├── types.ts        # TypeScript type definitions
│   ├── App.tsx         # Main app component
│   └── index.tsx       # Entry point
├── Dockerfile          # Production Docker image
├── nginx.conf          # Nginx configuration with API proxying
└── package.json        # Dependencies and scripts
```

## API Integration

The dashboard consumes the following endpoints:

### Agent A
- `POST /run` - Submit URLs for processing
- `GET /task/{task_id}` - Get task status

### Agent B
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Get specific task status

### Agent C Queue
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Get specific task status

## License

MIT
