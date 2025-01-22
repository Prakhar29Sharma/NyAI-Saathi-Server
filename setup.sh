#!/bin/bash

# Set up Python environment
export PYTHONPATH=$PWD

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file if it doesn't exist
cd app
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
GOOGLE_API_KEY=""
HUGGINGFACE_TOKEN=""
QDRANT_HOST="localhost"
QDRANT_PORT="6333"
COLLECTION_NAME="legal_documents"
VECTOR_SIZE=384
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
EOL
    echo "Please add your GOOGLE_API_KEY and HUGGINGFACE_TOKEN to .env file"
fi

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker first."
    exit 1
fi

# Print setup completion message
echo "Setup completed!"
echo "Before running the server:"
echo "1. Make sure to add your GOOGLE_API_KEY to .env"
echo "2. Choose how to run the server:"
echo ""
echo "Option 1: Run with Docker Compose (recommended)"
echo "$ docker-compose up --build"
echo ""
echo "Option 2: Run locally with Uvicorn"
echo "$ uvicorn app.main:app --reload"
echo ""
echo "Option 3: Run tests"
echo "$ pytest"
