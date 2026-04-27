# Gemini OCR Migration Plan (Go Branch)

## 1. Gemini API Free Tier Limits
The Google AI Studio "Gemini API Free Tier" is very generous for development and small-scale apps:
*   **Gemini 2.0 Flash:**
    *   **Rate Limit:** 15 Requests Per Minute (RPM)
    *   **Daily Limit:** 1,500 Requests Per Day
*   **Gemini 1.5 Flash:**
    *   **Rate Limit:** 15 Requests Per Minute (RPM)
    *   **Daily Limit:** 1,500 Requests Per Day

This is perfectly suited for your OCR project.

## 2. Go SDK
Yes, Google provides an official, high-quality Go SDK:
[https://github.com/google/generative-ai-go](https://github.com/google/generative-ai-go)

## 3. Migration Strategy (Go Branch)

### Step 1: Create Branch
```bash
git checkout -b feature/gemini-migration-go
```

### Step 2: Dependencies
You will remove `paddleocr`, `opencv-python`, and other heavy dependencies from `requirements.txt` (or update `go.mod` if switching language entirely). 

*Note: Since your current project is a Go project (seen in `go.mod`), migrating the extraction logic to Go is the most idiomatic and efficient path.*

### Step 3: Implementation Pattern
Your new Go service will be simple:
1.  **Accept HTTP Request** (Multipart file upload).
2.  **Read Image Bytes.**
3.  **Client Call:** Send image to `generativeai` with a system instruction:
    *"You are a receipt parsing assistant. Return ONLY JSON with fields: merchant_name, date, total_amount, items."*
4.  **Unmarshal JSON** and return.

### Step 4: Security
*   **API Key:** Store in Render's environment variables as `GEMINI_API_KEY`.
*   **Never** commit the key to Git.

## 4. Next Steps
1.  Let's verify your `go.mod` to ensure it's ready.
2.  I will help you write the `gemini_service.go` file.
3.  We will remove the heavy OCR dependencies to drastically reduce the container size.

Shall we proceed with switching to the Go branch and installing the Go GenAI SDK?
