#!/bin/bash

set -e  # Exit immediately if a command fails

# Print colorful banner
echo -e "\033[1;34m"
echo "==========================================="
echo "  NyAI Saathi - Cloud VM Setup Script"
echo "==========================================="
echo -e "\033[0m"

# Function to check and install system dependencies
install_dependencies() {
    echo -e "\033[1;36m\nInstalling system dependencies...\033[0m"
    
    # Update package lists
    sudo apt-get update
    
    # Install required packages
    sudo apt-get install -y \
        python3 python3-pip python3-venv \
        docker.io docker-compose \
        curl wget git
    
    # Start Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    echo -e "\033[1;32mSystem dependencies installed successfully!\033[0m"
    echo -e "\033[1;33mNOTE: You may need to log out and back in for Docker permissions to take effect.\033[0m"
}

# Function to setup Python environment
setup_python_env() {
    echo -e "\033[1;36m\nSetting up Python environment...\033[0m"
    
    # Create virtual environment
    python3 -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Set PYTHONPATH
    export PYTHONPATH=$PWD
    
    echo -e "\033[1;32mPython environment setup completed!\033[0m"
}

# Function to create configuration files
setup_config() {
    echo -e "\033[1;36m\nSetting up configuration files...\033[0m"
    
    # Create app directory if it doesn't exist
    mkdir -p app

    # Create .env file if it doesn't exist
    if [ ! -f app/.env ]; then
        echo "Creating .env file..."
        cat > app/.env << EOL
# API Keys
GOOGLE_API_KEY=""
HUGGINGFACE_TOKEN=""

# Qdrant Configuration
QDRANT_HOST="qdrant"  # Use "qdrant" for Docker, "localhost" for local dev
QDRANT_PORT="6333"
COLLECTION_NAME="legal_documents"
COLLECTION_NAME2="legal_knowledge"
VECTOR_SIZE=384
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
EOL
        echo -e "\033[1;32m.env file created successfully!\033[0m"
    else
        echo -e "\033[1;33m.env file already exists, skipping...\033[0m"
    fi
    
    # Configure CORS for cloud deployment
    if [ -f app/main.py ]; then
        echo "Updating CORS settings for cloud deployment..."
        sed -i 's/allow_origins=\["http:\/\/localhost:3000"\]/allow_origins=["*"]/' app/main.py
        echo -e "\033[1;32mCORS settings updated for cloud deployment.\033[0m"
    fi
}

# Function to setup Docker
setup_docker() {
    echo -e "\033[1;36m\nSetting up Docker environment...\033[0m"
    
    # Create docker-compose.yml if it doesn't exist
    if [ ! -f docker-compose.yml ]; then
        echo "Creating docker-compose.yml file..."
        cat > docker-compose.yml << EOL
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    container_name: qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - nyai-network

  api:
    build: .
    restart: always
    container_name: nyai-api
    depends_on:
      - qdrant
    ports:
      - "80:8000"
    environment:
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - HUGGINGFACE_TOKEN=\${HUGGINGFACE_TOKEN}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - COLLECTION_NAME=\${COLLECTION_NAME:-legal_documents}
      - COLLECTION_NAME2=\${COLLECTION_NAME2:-legal_knowledge}
      - VECTOR_SIZE=\${VECTOR_SIZE:-384}
      - EMBEDDING_MODEL=\${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}
    volumes:
      - ./app:/app/app
    networks:
      - nyai-network

volumes:
  qdrant_data:
    driver: local

networks:
  nyai-network:
    driver: bridge
EOL
        echo -e "\033[1;32mdocker-compose.yml created successfully!\033[0m"
    else
        echo -e "\033[1;33mdocker-compose.yml already exists, skipping...\033[0m"
    fi
    
    # Create Dockerfile if it doesn't exist
    if [ ! -f Dockerfile ]; then
        echo "Creating Dockerfile..."
        cat > Dockerfile << EOL
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Make port 8000 available
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOL
        echo -e "\033[1;32mDockerfile created successfully!\033[0m"
    else
        echo -e "\033[1;33mDockerfile already exists, skipping...\033[0m"
    fi
}

# Function to configure firewall
configure_firewall() {
    echo -e "\033[1;36m\nConfiguring firewall...\033[0m"
    
    if command -v ufw > /dev/null; then
        echo "Setting up UFW firewall rules..."
        sudo ufw allow 22/tcp  # SSH
        sudo ufw allow 80/tcp  # HTTP
        
        # Only enable if not already enabled
        if ! sudo ufw status | grep -q "Status: active"; then
            echo "y" | sudo ufw enable
        fi
        
        echo -e "\033[1;32mFirewall configured successfully!\033[0m"
    else
        echo -e "\033[1;33mUFW not found, skipping firewall configuration.\033[0m"
    fi
}

# Function to setup API keys
setup_api_keys() {
    echo -e "\033[1;36m\nSetting up API keys...\033[0m"
    
    # Check if .env exists and has empty API keys
    if [ -f app/.env ] && grep -q 'GOOGLE_API_KEY=""' app/.env; then
        echo -e "\033[1;33mAPI keys need to be configured.\033[0m"
        
        # Ask for API keys
        read -p "Enter your Google API Key (leave blank to skip): " google_key
        read -p "Enter your HuggingFace Token (leave blank to skip): " huggingface_token
        
        # Update .env file if keys were provided
        if [ ! -z "$google_key" ]; then
            sed -i "s/GOOGLE_API_KEY=\"\"/GOOGLE_API_KEY=\"$google_key\"/" app/.env
            echo -e "\033[1;32mGoogle API Key set successfully!\033[0m"
        fi
        
        if [ ! -z "$huggingface_token" ]; then
            sed -i "s/HUGGINGFACE_TOKEN=\"\"/HUGGINGFACE_TOKEN=\"$huggingface_token\"/" app/.env
            echo -e "\033[1;32mHuggingFace Token set successfully!\033[0m"
        fi
    else
        echo -e "\033[1;33mAPI keys appear to be already configured or .env file is missing.\033[0m"
    fi
}

# Function to start services
start_services() {
    echo -e "\033[1;36m\nStarting services...\033[0m"
    
    # Create necessary directories
    mkdir -p app/static/assets
    mkdir -p app/static/css
    mkdir -p app/static/js
    mkdir -p app/templates
    
    # Start Docker containers
    if [ -f docker-compose.yml ]; then
        echo "Starting Docker containers..."
        docker-compose up -d
        
        echo -e "\033[1;32mServices started successfully!\033[0m"
    else
        echo -e "\033[1;31mError: docker-compose.yml not found\033[0m"
    fi
}

# Main function
main() {
    # Ask what to install
    echo -e "\033[1;37mWelcome to NyAI Saathi setup!\033[0m"
    echo -e "\033[1;37mThis script will help you set up the project on a cloud VM.\033[0m"
    echo ""
    
    # Check if running as root and display warning if needed
    if [ "$EUID" -ne 0 ]; then
        echo -e "\033[1;33mNote: Some operations might require sudo privileges.\033[0m"
        echo ""
    fi
    
    # System dependencies
    read -p "Install system dependencies (Docker, Python, etc.)? (y/n, default: y): " install_deps
    install_deps=${install_deps:-y}
    if [[ "$install_deps" =~ ^[Yy]$ ]]; then
        install_dependencies
    fi
    
    # Python environment
    read -p "Set up Python environment? (y/n, default: y): " setup_py
    setup_py=${setup_py:-y}
    if [[ "$setup_py" =~ ^[Yy]$ ]]; then
        setup_python_env
    fi
    
    # Configuration
    read -p "Set up configuration files? (y/n, default: y): " setup_conf
    setup_conf=${setup_conf:-y}
    if [[ "$setup_conf" =~ ^[Yy]$ ]]; then
        setup_config
    fi
    
    # Docker
    read -p "Set up Docker environment? (y/n, default: y): " setup_dock
    setup_dock=${setup_dock:-y}
    if [[ "$setup_dock" =~ ^[Yy]$ ]]; then
        setup_docker
    fi
    
    # Firewall
    read -p "Configure firewall? (y/n, default: y): " conf_firewall
    conf_firewall=${conf_firewall:-y}
    if [[ "$conf_firewall" =~ ^[Yy]$ ]]; then
        configure_firewall
    fi
    
    # API Keys
    read -p "Configure API keys? (y/n, default: y): " setup_keys
    setup_keys=${setup_keys:-y}
    if [[ "$setup_keys" =~ ^[Yy]$ ]]; then
        setup_api_keys
    fi
    
    # Start services
    read -p "Start services now? (y/n, default: y): " start_now
    start_now=${start_now:-y}
    if [[ "$start_now" =~ ^[Yy]$ ]]; then
        start_services
    fi
    
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
    
    # Display completion message
    echo -e "\033[1;32m"
    echo "==========================================="
    echo "  NyAI Saathi Setup Complete!"
    echo "==========================================="
    echo -e "\033[0m"
    echo ""
    echo -e "\033[1;36mYour server should be available at:\033[0m"
    echo "http://$SERVER_IP"
    echo ""
    echo -e "\033[1;36mPipeline Visualizer:\033[0m"
    echo "http://$SERVER_IP/api/v1/visualizer"
    echo ""
    echo -e "\033[1;36mUseful commands:\033[0m"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop server:  docker-compose down"
    echo "  Start server: docker-compose up -d"
    echo "  Restart:      docker-compose restart"
    echo ""
    echo -e "\033[1;33mNote: If you just added your user to the docker group, you may need to log out and back in for it to take effect.\033[0m"
    echo ""
}

# Run the main function
main

exit 0