# 🚀 ICE Enterprise Installation Guide

Deploying the ICE Engine requires satisfying strict hardware security requirements and integrating with standard enterprise infrastructure.

## 1. Prerequisites
*   **PostgreSQL**: (Required) Used for the persistent episodic memory ledger. MUST have the `pgvector` extension enabled.
*   **Redis**: (Required) Used for high-speed hot-context caching and session synchronization.
*   **Docker / Kubernetes**: Highly recommended for enterprise-scale deployments.

## 2. Hardware-Bound Licensing
ICE is cryptographically secured to your authorized infrastructure. 

### Activating Your Node
To run ICE, you must be issued an `ICE_LICENSE_JWT` by your Dopove account manager. 
Export this token on your host machine or inject it into your Kubernetes Secrets:
```bash
export ICE_LICENSE_JWT="<your_enterprise_token>"
```

Upon the first successful boot, ICE will verify the cryptographic signature and create a permanent offline seal (`~/.ice/license.ice`). Future reboots on the same physical or virtual machine will automatically bypass external validation using this seal, allowing for secure air-gapped execution.

---

## 3. Quick Start (Docker Compose)

For containerized environments, the fastest way to get started is using our pre-configured Docker Compose topology.

We have provided a production-ready template in your distribution package at `client_demos/deployment/docker/docker-compose.yml`.

**To start the stack:**
```bash
export ICE_LICENSE_JWT="<your_token>"
cd client_demos/deployment/docker
docker-compose up -d
```
This will spin up the ICE Engine, a pgvector-enabled PostgreSQL instance, and a Redis cache.

---

## 4. Kubernetes (K8s) Deployment

For true enterprise scale (10,000+ users), deploy ICE to your Kubernetes cluster. The ICE Engine is mathematically stateless and can be horizontally scaled infinitely.

We have provided a complete suite of Kubernetes manifests in `client_demos/deployment/kubernetes/`:
*   `01-configmap.yaml`: Define memory caps and chunk sizes.
*   `02-secrets.yaml`: Securely store your JWT and DB credentials.
*   `03-deployment.yaml`: The embedded engine pods.
*   `04-service.yaml`: Internal cluster routing.
*   `05-hpa.yaml`: Horizontal Pod Autoscaler based on CPU/Memory usage.

**To deploy:**
```bash
cd client_demos/deployment/kubernetes/
kubectl apply -f .
```

---

## 5. Starting the Engine (Bare Metal / VM)
If you are deploying on bare metal without containers, ensure PostgreSQL and Redis are running, then install the correct ICE package for your environment.

### A. Installing the Python SDK
The Python builds are located in the `dist/python/` directory. You must choose the wheel file that matches your **subscription tier**, **Python version**, and **CPU architecture**.

The filename format is: `ice_<tier>-<version>-<python_tag>-<arch>.whl`

**Example:** For an **Enterprise** tier license on Python **3.11** and an **x86_64** machine, you would install:
```bash
pip install dist/python/ice_enterprise-3.0.0-cp311-cp311-manylinux2014_x86_64.whl
```

### B. Installing the Node.js SDK
The Node.js builds are located in the `dist/node/` directory. Choose the package that corresponds to your subscription tier.

**Example:** For a **Community** tier license, you would install:
```bash
npm install dist/node/ice-node-community-3.0.0.tgz
```

### C. Launching the Server
Once the package is installed, set your environment variables and start the engine via the CLI:
```bash
# Ensure your environment variables are set
export DATABASE_URL="postgres://user:pass@host/db"
export REDIS_URL="redis://host:6379/0"
export ICE_LICENSE_JWT="<your_token>"

# Launch the server
ice serve --host 0.0.0.0 --port 8008 --workers 4
```
