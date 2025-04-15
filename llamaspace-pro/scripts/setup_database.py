#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database Setup Script for LlamaSpace Pro

This script initializes all databases required for LlamaSpace Pro:
- TimescaleDB for telemetry data
- MongoDB for configuration and document storage
- Redis for caching and pub/sub
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import dotenv
import pymongo
import redis
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("db_setup")

# Create console for rich output
console = Console()

# Load environment variables
dotenv.load_dotenv()

# Root directory
ROOT_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"

# Database connection parameters
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "llamaspace")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "llamaspace")
PG_DB = os.getenv("POSTGRES_DB", "llamaspace")

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_USER = os.getenv("MONGO_USER", "llamaspace")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "llamaspace")
MONGO_DB = os.getenv("MONGO_DB", "llamaspace")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")


# Check if Docker is available
def is_docker_available():
    try:
        subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# Function to start Docker containers for databases
def start_docker_databases():
    console.print(
        Panel.fit("Starting Docker containers for databases", style="bold blue")
    )

    # Create Docker network if it doesn't exist
    subprocess.run(
        ["docker", "network", "create", "--driver", "bridge", "llamaspace-network"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Check if containers are already running
    containers = {"timescaledb": False, "mongodb": False, "redis": False}

    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    running_containers = result.stdout.strip().split("\n")
    for container in running_containers:
        if container == "llamaspace-timescaledb":
            containers["timescaledb"] = True
        elif container == "llamaspace-mongodb":
            containers["mongodb"] = True
        elif container == "llamaspace-redis":
            containers["redis"] = True

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Start TimescaleDB if not running
        if not containers["timescaledb"]:
            task = progress.add_task("[cyan]Starting TimescaleDB...", total=None)
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    "llamaspace-timescaledb",
                    "--network",
                    "llamaspace-network",
                    "-e",
                    f"POSTGRES_USER={PG_USER}",
                    "-e",
                    f"POSTGRES_PASSWORD={PG_PASSWORD}",
                    "-e",
                    f"POSTGRES_DB={PG_DB}",
                    "-p",
                    f"{PG_PORT}:5432",
                    "-v",
                    "llamaspace-timescaledb-data:/var/lib/postgresql/data",
                    "timescale/timescaledb:latest-pg14",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            progress.update(task, description="[green]TimescaleDB started")
        else:
            progress.add_task("[green]TimescaleDB is already running", completed=True)

        # Start MongoDB if not running
        if not containers["mongodb"]:
            task = progress.add_task("[cyan]Starting MongoDB...", total=None)
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    "llamaspace-mongodb",
                    "--network",
                    "llamaspace-network",
                    "-e",
                    f"MONGO_INITDB_ROOT_USERNAME={MONGO_USER}",
                    "-e",
                    f"MONGO_INITDB_ROOT_PASSWORD={MONGO_PASSWORD}",
                    "-p",
                    f"{MONGO_PORT}:27017",
                    "-v",
                    "llamaspace-mongodb-data:/data/db",
                    "mongo:latest",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            progress.update(task, description="[green]MongoDB started")
        else:
            progress.add_task("[green]MongoDB is already running", completed=True)

        # Start Redis if not running
        if not containers["redis"]:
            task = progress.add_task("[cyan]Starting Redis...", total=None)
            cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                "llamaspace-redis",
                "--network",
                "llamaspace-network",
                "-p",
                f"{REDIS_PORT}:6379",
                "-v",
                "llamaspace-redis-data:/data",
            ]

            if REDIS_PASSWORD:
                cmd.extend(["-e", f"REDIS_PASSWORD={REDIS_PASSWORD}"])

            cmd.append("redis:latest")

            if REDIS_PASSWORD:
                cmd.extend(["--requirepass", REDIS_PASSWORD])

            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            progress.update(task, description="[green]Redis started")
        else:
            progress.add_task("[green]Redis is already running", completed=True)

    # Wait for databases to be ready
    console.print("[yellow]Waiting for databases to be ready...[/yellow]")
    time.sleep(5)


# Initialize TimescaleDB
def setup_timescaledb():
    console.print(Panel.fit("Setting up TimescaleDB", style="bold blue"))

    # Connection string
    db_uri = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"

    # Connect to database
    try:
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            # Check if TimescaleDB extension is installed
            result = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            )
            extension_exists = result.fetchone() is not None

            if not extension_exists:
                conn.execute(
                    text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                )
                console.print("[green]TimescaleDB extension created[/green]")

            # Create hypertables for telemetry data
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS satellite_telemetry (
                    time TIMESTAMPTZ NOT NULL,
                    satellite_id TEXT NOT NULL,
                    subsystem TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    value DOUBLE PRECISION,
                    status TEXT,
                    metadata JSONB
                );
            """
                )
            )

            # Make it a hypertable
            try:
                conn.execute(
                    text(
                        """
                    SELECT create_hypertable('satellite_telemetry', 'time', if_not_exists => TRUE);
                """
                    )
                )
            except Exception as e:
                if "already a hypertable" not in str(e):
                    raise

            # Create indexes
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_satellite_telemetry_satellite_id ON satellite_telemetry (satellite_id);
                CREATE INDEX IF NOT EXISTS idx_satellite_telemetry_subsystem ON satellite_telemetry (subsystem);
                CREATE INDEX IF NOT EXISTS idx_satellite_telemetry_parameter ON satellite_telemetry (parameter);
            """
                )
            )

            # Create orbit table
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS satellite_orbits (
                    time TIMESTAMPTZ NOT NULL,
                    satellite_id TEXT NOT NULL,
                    position_x DOUBLE PRECISION,
                    position_y DOUBLE PRECISION,
                    position_z DOUBLE PRECISION,
                    velocity_x DOUBLE PRECISION,
                    velocity_y DOUBLE PRECISION,
                    velocity_z DOUBLE PRECISION,
                    metadata JSONB
                );
            """
                )
            )

            # Make it a hypertable
            try:
                conn.execute(
                    text(
                        """
                    SELECT create_hypertable('satellite_orbits', 'time', if_not_exists => TRUE);
                """
                    )
                )
            except Exception as e:
                if "already a hypertable" not in str(e):
                    raise

            # Create maneuver table
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS satellite_maneuvers (
                    id SERIAL PRIMARY KEY,
                    satellite_id TEXT NOT NULL,
                    start_time TIMESTAMPTZ NOT NULL,
                    end_time TIMESTAMPTZ,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    delta_v_x DOUBLE PRECISION,
                    delta_v_y DOUBLE PRECISION,
                    delta_v_z DOUBLE PRECISION,
                    fuel_used DOUBLE PRECISION,
                    success BOOLEAN,
                    description TEXT,
                    parameters JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """
                )
            )

            console.print("[green]TimescaleDB tables and hypertables created[/green]")

    except OperationalError as e:
        console.print(f"[red]Error connecting to TimescaleDB: {e}[/red]")
        if "Connection refused" in str(e):
            console.print(
                "[yellow]Make sure TimescaleDB is running and accessible[/yellow]"
            )
        return False

    return True


# Initialize MongoDB
def setup_mongodb():
    console.print(Panel.fit("Setting up MongoDB", style="bold blue"))

    # Connection string
    if MONGO_USER and MONGO_PASSWORD:
        mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
    else:
        mongo_uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"

    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(mongo_uri)
        db = client[MONGO_DB]

        # Create collections with validation schemas

        # Satellites collection
        db.create_collection(
            "satellites",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["satellite_id", "name", "type", "status"],
                    "properties": {
                        "satellite_id": {"bsonType": "string"},
                        "name": {"bsonType": "string"},
                        "type": {"bsonType": "string"},
                        "status": {"bsonType": "string"},
                        "launch_date": {"bsonType": "date"},
                        "mission": {"bsonType": "string"},
                        "owner": {"bsonType": "string"},
                        "tle": {
                            "bsonType": "object",
                            "properties": {
                                "line1": {"bsonType": "string"},
                                "line2": {"bsonType": "string"},
                                "epoch": {"bsonType": "date"},
                            },
                        },
                        "subsystems": {"bsonType": "array"},
                        "metadata": {"bsonType": "object"},
                    },
                }
            },
        )

        # Ground Stations collection
        db.create_collection(
            "ground_stations",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["station_id", "name", "location"],
                    "properties": {
                        "station_id": {"bsonType": "string"},
                        "name": {"bsonType": "string"},
                        "location": {
                            "bsonType": "object",
                            "required": ["latitude", "longitude"],
                            "properties": {
                                "latitude": {"bsonType": "double"},
                                "longitude": {"bsonType": "double"},
                                "altitude": {"bsonType": "double"},
                            },
                        },
                        "capabilities": {"bsonType": "array"},
                        "status": {"bsonType": "string"},
                        "metadata": {"bsonType": "object"},
                    },
                }
            },
        )

        # Users collection
        db.create_collection(
            "users",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["username", "email", "role"],
                    "properties": {
                        "username": {"bsonType": "string"},
                        "email": {"bsonType": "string"},
                        "first_name": {"bsonType": "string"},
                        "last_name": {"bsonType": "string"},
                        "role": {"bsonType": "string"},
                        "permissions": {"bsonType": "array"},
                        "created_at": {"bsonType": "date"},
                        "last_login": {"bsonType": "date"},
                        "settings": {"bsonType": "object"},
                    },
                }
            },
        )

        # Mission Plans collection
        db.create_collection(
            "mission_plans",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["plan_id", "name", "satellite_id", "status"],
                    "properties": {
                        "plan_id": {"bsonType": "string"},
                        "name": {"bsonType": "string"},
                        "satellite_id": {"bsonType": "string"},
                        "created_by": {"bsonType": "string"},
                        "created_at": {"bsonType": "date"},
                        "status": {"bsonType": "string"},
                        "start_time": {"bsonType": "date"},
                        "end_time": {"bsonType": "date"},
                        "activities": {"bsonType": "array"},
                        "metadata": {"bsonType": "object"},
                    },
                }
            },
        )

        # Create indexes
        db.satellites.create_index("satellite_id", unique=True)
        db.ground_stations.create_index("station_id", unique=True)
        db.users.create_index("username", unique=True)
        db.users.create_index("email", unique=True)
        db.mission_plans.create_index("plan_id", unique=True)
        db.mission_plans.create_index("satellite_id")

        console.print("[green]MongoDB collections and indexes created[/green]")

        # Insert sample data if collections are empty
        if db.satellites.count_documents({}) == 0:
            # Load sample data from YAML files if available
            sample_data_path = DATA_DIR / "samples"
            if (sample_data_path / "satellites.yaml").exists():
                with open(sample_data_path / "satellites.yaml", "r") as f:
                    satellites = yaml.safe_load(f)
                    db.satellites.insert_many(satellites)
                console.print("[green]Sample satellite data loaded[/green]")

        if db.ground_stations.count_documents({}) == 0:
            if (sample_data_path / "ground_stations.yaml").exists():
                with open(sample_data_path / "ground_stations.yaml", "r") as f:
                    stations = yaml.safe_load(f)
                    db.ground_stations.insert_many(stations)
                console.print("[green]Sample ground station data loaded[/green]")

        # Create default admin user if no users exist
        if db.users.count_documents({}) == 0:
            db.users.insert_one(
                {
                    "username": "admin",
                    "email": "admin@llamaspace.io",
                    "first_name": "Admin",
                    "last_name": "User",
                    "role": "admin",
                    "permissions": ["*"],
                    "created_at": datetime.datetime.utcnow(),
                    "settings": {"theme": "dark", "notifications_enabled": True},
                }
            )
            console.print("[green]Default admin user created[/green]")

    except pymongo.errors.ConnectionFailure as e:
        console.print(f"[red]Error connecting to MongoDB: {e}[/red]")
        console.print("[yellow]Make sure MongoDB is running and accessible[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Error setting up MongoDB: {e}[/red]")
        return False

    return True


# Initialize Redis
def setup_redis():
    console.print(Panel.fit("Setting up Redis", style="bold blue"))

    try:
        # Connect to Redis
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            decode_responses=True,
        )

        # Test connection
        r.ping()

        # Create key prefixes for different data types
        key_prefixes = {
            "cache": "llamaspace:cache:",
            "session": "llamaspace:session:",
            "queue": "llamaspace:queue:",
            "lock": "llamaspace:lock:",
            "rate_limit": "llamaspace:rate_limit:",
            "pub_sub": "llamaspace:pubsub:",
        }

        # Store key prefixes
        r.hset("llamaspace:config:key_prefixes", mapping=key_prefixes)

        # Set up pub/sub channels
        channels = [
            "telemetry_stream",
            "command_stream",
            "alert_stream",
            "status_updates",
            "user_notifications",
        ]

        for channel in channels:
            # Publish a system message to initialize channels
            r.publish(
                f"{key_prefixes['pub_sub']}{channel}",
                json.dumps(
                    {
                        "type": "system",
                        "message": f"Channel {channel} initialized",
                        "timestamp": time.time(),
                    }
                ),
            )

        # Store some configuration in Redis
        r.hset(
            "llamaspace:config:app",
            mapping={
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "initialized_at": str(int(time.time())),
            },
        )

        console.print("[green]Redis initialized successfully[/green]")

    except redis.exceptions.ConnectionError as e:
        console.print(f"[red]Error connecting to Redis: {e}[/red]")
        console.print("[yellow]Make sure Redis is running and accessible[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Error setting up Redis: {e}[/red]")
        return False

    return True


# Main function
def main():
    console.print(Panel.fit("LlamaSpace Pro Database Setup", style="bold cyan"))

    # Check if Docker is available and start containers if needed
    if is_docker_available():
        start_docker_databases()
    else:
        console.print(
            "[yellow]Docker not found. Assuming databases are already running.[/yellow]"
        )
        console.print(
            "[yellow]If databases are not running, please start them manually.[/yellow]"
        )

    # Create required directories
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "db").mkdir(exist_ok=True)
    (DATA_DIR / "samples").mkdir(exist_ok=True)

    # Setup each database
    timescaledb_success = setup_timescaledb()
    mongodb_success = setup_mongodb()
    redis_success = setup_redis()

    # Summary
    console.print("\n" + Panel.fit("Setup Summary", style="bold cyan"))
    console.print(
        f"TimescaleDB: {'[green]SUCCESS[/green]' if timescaledb_success else '[red]FAILED[/red]'}"
    )
    console.print(
        f"MongoDB:     {'[green]SUCCESS[/green]' if mongodb_success else '[red]FAILED[/red]'}"
    )
    console.print(
        f"Redis:       {'[green]SUCCESS[/green]' if redis_success else '[red]FAILED[/red]'}"
    )

    if timescaledb_success and mongodb_success and redis_success:
        console.print("\n[green bold]All databases successfully set up![/green bold]")
        return 0
    else:
        console.print(
            "\n[yellow]Some database setups failed. Check the logs above for details.[/yellow]"
        )
        return 1


if __name__ == "__main__":
    # Import here to avoid circular imports
    import datetime

    sys.exit(main())
