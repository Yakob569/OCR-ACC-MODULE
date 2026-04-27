# OCR-ACC-MODULE Development History & Status

## Overview
We are building a receipt OCR service. Originally, we used **PaddleOCR** (a heavy local OCR engine). We migrated to the **Google Gemini API** to resolve memory issues, improve accuracy, and enable efficient deployment on free-tier services like Render.

## Key Issues Encountered
1.  **Memory Constraints (Render Free Tier):** The 512MB RAM limit was being exceeded by heavy PaddleOCR model downloads and processing. 
    *   *Solution:* Offloaded OCR to **Gemini 2.0 Flash API**.
2.  **Deployment Disk Full:** The container build process and model caching filled the ephemeral disk.
    *   *Solution:* Switched to pre-built image deployment via **GitHub Container Registry (GHCR)** and configured a persistent Render disk mount at `/root/.paddleocr`.
3.  **Inaccurate Extraction:** Initial regex-based parsing failed on varying receipt layouts.
    *   *Solution:* Replaced regex with **Gemini LLM reasoning**, which natively understands receipt structures.

## Current Project State (as of April 27, 2026)
- **Branch:** `feature/gemini-migration-go` (Python-based but migrated to Gemini SDK).
- **Core Engine:** Gemini 2.0 Flash (API-based extraction).
- **Deployment Pipeline:** Automated via GitHub Actions (deploying to GHCR).
- **Dependencies:** Lightweight (PaddleOCR and related heavy libraries removed).

## Next Steps
1.  **Production Readiness:**
    *   Push the current branch to GitHub to trigger the automated build.
    *   Add `GEMINI_API_KEY` to Render's Environment Variables.
2.  **Validation:** Perform final end-to-end testing with your receipt images to confirm accuracy with the new LLM-based extraction.
3.  **Persistence:** Ensure the Render persistent disk is correctly mounted if any caching is still needed.
