# AI Code Review Agent

A developer tool that analyzes GitHub pull requests and flags bugs, security issues, and code quality problems. It uses a hybrid approach, combining fast deterministic rule checks with deep LLM-based analysis to provide high-signal feedback.

## Screenshots

| Diff Analysis | Finding Details |
| :---: | :---: |
| ![Screenshot 1](screenshots/1.png) | ![Screenshot 2](screenshots/2.png) |
| **Evaluation Metrics** | **Review List** |
| ![Screenshot 3](screenshots/3.png) | ![Screenshot 4](screenshots/4.png) |

<br>
<p align="center">
  <b>Full Dashboard View</b><br>
  <img src="screenshots/5.png" width="100%" />
</p>

## Architecture

```mermaid
flowchart TD
    User([User]) --> UI[Frontend (React/Vite)]
    UI --> API[Backend API (FastAPI)]
    API --> GitHub[GitHub API]
    GitHub --> API
    
    API --> Engine[Analysis Engine]
    
    subgraph Engine [Analysis Engine]
        Rules["Deterministic Rules<br>Secrets, SQLi, Exceptions"]
        LLM["LLM Review<br>Groq / Gemini / OpenRouter"]
        Rules --> Merge[Merge & Deduplicate]
        LLM --> Merge
    end
    
    Engine --> DB[(SQLite DB)]
    DB --> API
```

## Setup and Running

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in your keys:
   - `GITHUB_TOKEN`: Required to fetch PR diffs. A fine-grained PAT with read access to the target repository is sufficient.
   - `GEMINI_API_KEY`: Primary API key for LLM analysis.
   - `OPENROUTER_API_KEY`: Fallback API key for LLM analysis.
3. Start the application using Docker Compose:

```bash
docker-compose up --build
```

4. Open `http://localhost:3000` in your browser.

## Evaluation Suite

This project includes a deterministic evaluation suite testing the engine against 10 Python code fixtures containing known vulnerabilities and clean code.

To view the results:
- Ensure the backend is running.
- Navigate to the `Eval` tab in the web UI.

### Summary Results
The engine is evaluated on Precision (how many reported findings are real), Recall (how many real issues were found), and F1 Score (harmonic mean of precision and recall).
