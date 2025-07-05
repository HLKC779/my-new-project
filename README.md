# RAG System with Authentication and Real-time Chat

A full-stack Retrieval-Augmented Generation (RAG) system with real-time chat capabilities, built with FastAPI, React, and modern AI technologies.

## Features

- **Real-time Chat**: WebSocket-based chat interface with streaming responses
- **Document Management**: Upload, index, and manage various document types
- **Natural Language Search**: Query documents using natural language
- **Conversation History**: Save and retrieve chat conversations
- **User Authentication**: Secure JWT-based authentication
- **Responsive UI**: Modern, mobile-friendly interface
- **RESTful API**: Fully documented API for integration

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: SQLite (production: PostgreSQL)
- **Vector Store**: ChromaDB
- **Embeddings**: HuggingFace Sentence Transformers
- **LLM**: GPT-4 (or other models via OpenAI/HuggingFace)
- **Authentication**: JWT with OAuth2
- **Real-time**: WebSockets

### Frontend
- **Framework**: React 18
- **UI Library**: Material-UI (MUI)
- **State Management**: React Context API
- **Routing**: React Router 6
- **HTTP Client**: Axios
- **WebSocket**: Native WebSocket API

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn
- Git
- OpenAI API Key (for GPT models)

## Getting Started

### Backend Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd my-new-project/backend
   ```

2. Set up the Python virtual environment and install dependencies:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Initialize the database:
   ```bash
   # Run database migrations
   alembic upgrade head
   
   # Or create tables directly
   python -c "from app.db.base import init_db; init_db()"
   ```

5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Start the development server:
   ```bash
   npm start
   # or
   yarn start
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## API Documentation

Once the backend is running, you can access:

- **API Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

## Environment Variables

### Backend (`.env`)

```env
# Application
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./rag_system.db

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# RAG Settings
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
CHROMA_DB_PATH=./chroma_db
LLM_MODEL_NAME=gpt-4

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Project Structure

```
my-new-project/
├── backend/                    # Backend application
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── core/              # Core configuration
│   │   ├── db/                # Database configuration
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic models
│   │   ├── services/          # Business logic
│   │   └── main.py            # Application entry point
│   ├── tests/                 # Backend tests
│   ├── requirements.txt       # Python dependencies
│   └── .env                  # Environment variables
├── frontend/                  # Frontend application
│   ├── public/               # Static files
│   ├── src/                  # Source code
│   │   ├── components/       # Reusable components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   └── App.js            # Main App component
│   ├── package.json          # Frontend dependencies
│   └── .env                 # Frontend environment variables
├── .gitignore
└── README.md
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd ../frontend
npm test
```

### Code Formatting

```bash
# Backend
black .
isort .
flake8 .

# Frontend
cd frontend
npx prettier --write .
```

## Deployment

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Production

1. Set up a production database (PostgreSQL recommended)
2. Update environment variables for production
3. Use a production-grade ASGI server like Gunicorn with Uvicorn workers:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```
4. Set up a reverse proxy (Nginx, Caddy, etc.)
5. Configure SSL/TLS

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Your Name - [@your_twitter](https://twitter.com/your_twitter) - your.email@example.com

Project Link: [https://github.com/yourusername/rag-system](https://github.com/yourusername/rag-system)
