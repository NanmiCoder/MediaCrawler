# MediaCrawler Frontend UI

A modern web interface for configuring and running the MediaCrawler project.

## Features

- **Config Tab**: Visual interface to edit `base_config.py` settings
- **Crawler Tab**: Command builder and execution interface
- Modern UI built with Next.js, TypeScript, Tailwind CSS, and Shadcn UI
- Real-time command preview and execution
- Quick command templates for common use cases

## Setup Instructions

### Prerequisites

- Node.js 16.0.0 or higher
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

### Running the Frontend

1. Start the development server:
```bash
npm run dev
# or
yarn dev
```

2. Open [http://localhost:3000](http://localhost:3000) in your browser

### Backend API Setup

The frontend requires the FastAPI backend to be running. 

1. Navigate to the api directory:
```bash
cd ../api
```

2. Install Python dependencies:
```bash
uv pip install -r requirements.txt
```

3. Start the API server:
```bash
python main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

## Usage

### Config Tab
- Edit all MediaCrawler configuration settings through a visual interface
- Organized into logical sections: Basic Config, Crawler Settings, Proxy Settings, Advanced Settings
- Save changes directly to the `base_config.py` file

### Crawler Tab
- Build commands using dropdown menus and form inputs
- Preview the generated command before execution
- Execute commands and view real-time output
- Use quick command templates for common scenarios

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout
│   ├── page.tsx          # Main page with tabs
│   └── globals.css       # Global styles
├── components/            # React components
│   ├── ui/               # Shadcn UI components
│   ├── config-tab.tsx    # Configuration interface
│   └── crawler-tab.tsx   # Crawler command interface
├── lib/                  # Utility functions
│   └── utils.ts         # Common utilities
└── package.json         # Dependencies and scripts
```

## Technologies Used

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn UI**: Modern component library
- **Radix UI**: Unstyled, accessible components
- **Axios**: HTTP client for API requests

## API Endpoints

The frontend communicates with these API endpoints:

- `GET /config` - Fetch current configuration
- `POST /config` - Update configuration
- `POST /run-crawler` - Execute crawler command
- `GET /command-options` - Get available command options

## Contributing

This frontend is designed to work with the MediaCrawler project. Make sure the backend API is running and accessible before using the interface.

## License

This project follows the same license as the main MediaCrawler project. 