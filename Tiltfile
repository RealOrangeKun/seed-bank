# Tiltfile for Seed Bank Development Environment
# Run: tilt up

# Load environment variables
load_dot_env('.env')

# PostgreSQL Database
docker_compose('docker-compose.yml')

# API Service (with hot reload)
docker_build(
    'seed-bank-api',
    '.',
    dockerfile='Dockerfile',
    live_update=[
        sync('.', '/app'),
        run('pip install -r requirements.txt', trigger=['requirements.txt']),
    ],
    entrypoint=['python', 'main.py'],
)

# Frontend (if needed)
docker_build(
    'seed-bank-web',
    './frontend',
    dockerfile='Dockerfile',
)

# Port forwarding
k8s_resource('api', port_forwards=8000)
k8s_resource('adminer', port_forwards=8081)
k8s_resource('postgres', port_forwards=5432)
