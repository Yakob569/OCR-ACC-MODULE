# OCR Deployment Strategy: Render + GitHub Actions

To avoid "Disk Full" errors and slow deployments on Render, we will shift to a **"Push to Registry"** model.

## 1. Registry Choice (Do you need a Docker account?)
You have two great options:
*   **GitHub Container Registry (GHCR):** Highly recommended. It is built directly into GitHub. **You do NOT need a Docker Hub account.** It is free, private by default, and integrated with your repo.
*   **Docker Hub:** A standard alternative, but requires a separate account.

*We will use **GHCR** below.*

## 2. GitHub Actions Setup
Create `.github/workflows/deploy.yml` in your repository:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ "main" ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```

## 3. Configure Render
After you push the code above, GitHub will build your image. Now, set up Render:

1.  **Render Dashboard:**
    *   Click **New +** -> **Web Service**.
    *   Select **"Build and deploy from an image"**.
    *   **Image URL:** `ghcr.io/YAKOB569/OCR-ACC-USER-MODULE:latest` (Update this if your repo name is different).
    *   **Registry:** Select **GitHub Container Registry**.
2.  **Mount Persistent Disk (Crucial for PaddleOCR):**
    *   Go to your new Service on Render.
    *   Click **Disks** -> **Add Disk**.
    *   **Name:** `paddle-models`
    *   **Mount Path:** `/root/.paddleocr`
    *   **Size:** 1 GB (Should be plenty for the models).
    *   **Save.**

## 4. Final Environment Setup
Ensure your Render Service **Environment Variables** are set (you can see them in your current Render service):
*   `DATABASE_URL`, `DB_USER`, `DB_PASS`, `JWT_SECRET`, etc.
*   **Note:** If your app expects a `.env` file, Render's Environment Variables section replaces that need.
