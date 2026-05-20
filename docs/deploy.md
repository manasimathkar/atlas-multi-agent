# Deploying Atlas to AWS Lightsail Containers

Atlas ships as a single Docker image. The live demo runs on AWS Lightsail Containers, which pulls a public image and exposes it at a managed HTTPS URL.

## Prerequisites

- Docker installed locally.
- A Docker Hub account (or any public container registry).
- An AWS account with access to Lightsail.

## Step 1: Build and push the image

Lightsail runs x86 (amd64). If you build on Apple Silicon, cross-build explicitly:

```bash
docker login
docker buildx build --platform linux/amd64 -t <dockerhub-user>/atlas:latest --push .
```

Confirm the image appears under your Docker Hub repositories.

## Step 2: Create a Lightsail container service

1. Open the AWS Lightsail console and choose the **Containers** tab.
2. Click **Create container service**.
3. Pick a region near your users (the live demo uses Oregon, us-west-2).
4. Choose a power tier. Atlas needs roughly 2 GB of memory, so the Medium tier (2 GB RAM, 1 vCPU) is the comfortable choice; smaller tiers can work for light use.
5. Scale: 1 node.
6. Name the service and create it.

## Step 3: Create a deployment

On the service page, create a deployment with:

- **Image:** `<dockerhub-user>/atlas:latest`
- **Environment variables:**
  - `ANTHROPIC_API_KEY` (your Anthropic key)
  - `TAVILY_API_KEY` (your Tavily key)
  - `PORT` = `8080`
- **Open port:** `8080`, protocol HTTP.
- **Public endpoint:** the `atlas` container on port `8080`.
- **Health check path:** `/healthz`.

Click **Save and deploy**. Lightsail pulls the image, starts the container, runs health checks, and then assigns a public HTTPS URL of the form `https://<service>.<id>.<region>.cs.amazonlightsail.com`.

## Step 4: Verify

1. Open the public URL; the Atlas UI should load.
2. Run a sample query and confirm a sourced brief is produced.
3. Submit a prompt-injection string and confirm the input guardrail blocks it.
4. Check the service logs in the Lightsail console for the structured agent trace.

## Updating the deployment

Rebuild and push the image, then on the service page choose **Modify your deployment** and **Save and deploy** again to pull the new `latest` tag.

## Cost note

Lightsail container services bill per running hour by tier. Delete the service after a demo to stop charges.
