#!/bin/bash

# LlamaSpace Pro: Advanced Satellite Operations Platform
# Installation script for development environment

set -e # Exit on any error

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print LlamaSpace ASCII art
print_banner() {
  echo -e "${CYAN}"
  echo "  _      _                       _____                      _____           "
  echo " | |    | |                     / ____|                    |  __ \          "
  echo " | |    | | __ _ _ __ ___   __ | (___  _ __   __ _  ___ ___| |__) | __ ___  "
  echo " | |    | |/ _\` | '_ \` _ \ / _\` |\___ \| '_ \ / _\` |/ __/ _ \  ___/ '__/ _ \ "
  echo " | |____| | (_| | | | | | | (_| |____) | |_) | (_| | (_|  __/ |   | | | (_) |"
  echo " |______|_|\__,_|_| |_| |_|\__,_|_____/| .__/ \__,_|\___\___|_|   |_|  \___/ "
  echo "                                        | |                                  "
  echo "                                        |_|                                  "
  echo -e "${NC}"
  echo -e "${YELLOW}Advanced Satellite Operations Platform with ML${NC}"
  echo -e "${YELLOW}==============================================${NC}"
  echo ""
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to display progress
progress() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to display success
success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to display warnings
warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to display errors
error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check system requirements
check_system_requirements() {
  progress "Checking system requirements..."
  
  # Check operating system
  OS="$(uname)"
  if [[ "$OS" == "Darwin" ]]; then
    progress "Running on macOS."
    PACKAGE_MANAGER="brew"
  elif [[ "$OS" == "Linux" ]]; then
    progress "Running on Linux."
    if command_exists apt-get; then
      PACKAGE_MANAGER="apt"
    elif command_exists yum; then
      PACKAGE_MANAGER="yum"
    else
      error "Unsupported Linux distribution. Please install dependencies manually."
      exit 1
    fi
  else
    error "Unsupported operating system: $OS. This script supports macOS and Linux."
    exit 1
  fi
  
  # Check for Python 3.9+
  if ! command_exists python3; then
    progress "Installing Python 3.10..."
    if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
      brew install python@3.10
    elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
      sudo apt update
      sudo apt install -y python3.10 python3.10-venv python3.10-dev
    elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
      sudo yum install -y python3.10 python3.10-devel
    fi
  else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo "$PYTHON_VERSION" | cut -d. -f1-2) < "3.9" ]]; then
      progress "Python version $PYTHON_VERSION is lower than required 3.9+."
      progress "Installing Python 3.10..."
      if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
        brew install python@3.10
      elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        sudo apt update
        sudo apt install -y python3.10 python3.10-venv python3.10-dev
      elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
        sudo yum install -y python3.10 python3.10-devel
      fi
    else
      progress "Python $PYTHON_VERSION is already installed."
    fi
  fi
  
  # Check for Node.js
  if ! command_exists node; then
    progress "Installing Node.js..."
    if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
      brew install node
    elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
      curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
      sudo apt install -y nodejs
    elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
      curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
      sudo yum install -y nodejs
    fi
  else
    progress "Node.js is already installed."
  fi
  
  # Check for Docker
  if ! command_exists docker; then
    progress "Installing Docker..."
    if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
      brew install --cask docker
      open /Applications/Docker.app
      progress "Please wait for Docker to start and press Enter when ready..."
      read -r
    elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
      sudo apt update
      sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
      echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      sudo apt update
      sudo apt install -y docker-ce docker-ce-cli containerd.io
      sudo usermod -aG docker $USER
      progress "Docker installed. You may need to log out and log back in for group changes to take effect."
    elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
      sudo yum install -y yum-utils
      sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      sudo yum install -y docker-ce docker-ce-cli containerd.io
      sudo systemctl start docker
      sudo systemctl enable docker
      sudo usermod -aG docker $USER
      progress "Docker installed. You may need to log out and log back in for group changes to take effect."
    fi
  else
    progress "Docker is already installed."
  fi
  
  # Check for Docker Compose
  if ! command_exists docker-compose; then
    progress "Installing Docker Compose..."
    if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
      brew install docker-compose
    else
      DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
      sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
      sudo chmod +x /usr/local/bin/docker-compose
    fi
  else
    progress "Docker Compose is already installed."
  fi
  
  success "System requirements check completed."
}

# Create and activate virtual environment
setup_python_environment() {
  progress "Setting up Python virtual environment..."
  
  if [[ ! -d "venv" ]]; then
    python3 -m venv venv
  fi
  
  # Activate virtual environment
  source venv/bin/activate
  
  # Upgrade pip
  pip install --upgrade pip
  
  success "Python virtual environment created and activated."
}

# Install Python dependencies
install_python_dependencies() {
  progress "Installing Python dependencies..."
  
  pip install -r requirements.txt
  
  success "Python dependencies installed."
}

# Install JavaScript dependencies
install_js_dependencies() {
  progress "Installing JavaScript dependencies..."
  
  if [[ -d "src/ui/webapp" ]]; then
    cd src/ui/webapp
    npm install
    cd ../../..
  else
    warning "Frontend directory not found. Skipping JavaScript dependencies."
  fi
  
  success "JavaScript dependencies installed."
}

# Build frontend
build_frontend() {
  progress "Building frontend application..."
  
  if [[ -d "src/ui/webapp" ]]; then
    cd src/ui/webapp
    npm run build
    cd ../../..
    success "Frontend built successfully."
  else
    warning "Frontend directory not found. Skipping build."
  fi
}

# Initialize database
init_database() {
  progress "Initializing database..."
  
  # Create database directories if they don't exist
  mkdir -p data/db
  
  # Run database initialization script if it exists
  if [[ -f "scripts/setup_database.py" ]]; then
    python scripts/setup_database.py
    success "Database initialized successfully."
  else
    warning "Database initialization script not found. Skipping database setup."
  fi
}

# Main function
main() {
  print_banner
  
  # Parse command line arguments
  local skip_requirements=false
  local skip_frontend=false
  local skip_database=false
  
  while [[ $# -gt 0 ]]; do
    case $1 in
      --skip-requirements)
        skip_requirements=true
        shift
        ;;
      --skip-frontend)
        skip_frontend=true
        shift
        ;;
      --skip-database)
        skip_database=true
        shift
        ;;
      --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --skip-requirements  Skip system requirements check"
        echo "  --skip-frontend      Skip frontend build"
        echo "  --skip-database      Skip database initialization"
        echo "  --help               Show this help message"
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        echo "Use --help for usage information."
        exit 1
        ;;
    esac
  done
  
  # Check system requirements
  if [[ "$skip_requirements" == "false" ]]; then
    check_system_requirements
  fi
  
  # Setup Python environment
  setup_python_environment
  
  # Install dependencies
  install_python_dependencies
  
  if [[ "$skip_frontend" == "false" ]]; then
    install_js_dependencies
    build_frontend
  fi
  
  if [[ "$skip_database" == "false" ]]; then
    init_database
  fi
  
  success "Installation completed successfully!"
  success "To start LlamaSpace Pro, run: python scripts/start_services.py"
}

# Run main function
main "$@" 