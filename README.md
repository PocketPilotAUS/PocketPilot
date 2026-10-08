
# PocketPilot

PocketPilot is an intelligent personal finance assistant designed to help users track expenses, understand spending patterns, and make informed financial decisions.

The project is being developed as a university team project.

## Project Overview

PocketPilot aims to combine financial analysis, personalized budgeting, debt repayment planning, and AI-assisted recommendations in one application.

The current implementation focuses on transaction management, spending analysis, and AI-generated explanations.

## Implemented Features

### Transaction Management
- Add transactions with amount, category, description, and date.
- Retrieve saved transactions.
- Delete transactions.
- Store transactions persistently using SQLite.
- Validate transaction data.

### Spending Analysis
- Calculate total spending.
- Calculate spending by category.
- Calculate category percentages.
- Compare spending between two months.
- Analyze transactions stored in the database.

### Financial Recommendations
- Detect spending increases of 20% or more.
- Detect spending decreases of 20% or more.
- Generate rule-based financial recommendations.
- Generate recommendations using actual stored transactions.

### AI Integration
- Generate natural-language explanations of recommendations.
- Use Qwen3 4B through Ollama.
- Run the AI model locally or on another computer on the same private network.
- Return AI explanations through FastAPI.
- Handle unavailable AI services with an HTTP 503 response.

### Testing
- Automated unit tests for financial calculations.
- API tests using isolated SQLite databases.
- Mocked AI tests that do not require a running Ollama server.

## Planned Features

- Frontend dashboard.
- User authentication and account management.
- User-specific transaction storage.
- Smart budgeting and savings planning.
- Debt repayment planner using avalanche and snowball methods.
- Additional financial insights.
- Improved AI explanation validation.
- Deployment and security improvements.

## Technology Stack

**Backend:** Python 3.12, FastAPI, Uvicorn

**Database:** SQLite, SQLAlchemy

**Validation:** Pydantic

**AI:** Ollama, Qwen3 4B, OpenAI-compatible Python SDK

**Testing:** pytest, HTTPX, FastAPI TestClient

**Version Control:** Git and GitHub

## Project Structure

```text
PocketPilot/
├── Backend/
│   ├── app/
│   │   ├── algorithms/
│   │   ├── ai/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   ├── init_db.py
│   └── requirements.txt
├── docs/
├── data/
├── .gitignore
└── README.md
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/PocketPilotAUS/PocketPilot.git
cd PocketPilot/Backend
```

### 2. Create a Virtual Environment

```powershell
py -3.12 -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Initialize the Database

```powershell
python init_db.py
```

This creates the local SQLite database and transaction table.

### 5. Start the Backend

```powershell
python -m uvicorn app.main:app --reload
```

Open:

http://127.0.0.1:8000/docs

This displays the available FastAPI endpoints.

## AI Configuration

PocketPilot uses Qwen3 4B through Ollama.

Install Ollama on the computer that will host the AI model:

https://ollama.com/download

Download the model:

```powershell
ollama pull qwen3:4b
```

Create a `.env` file inside `Backend/` containing:

```env
OLLAMA_URL=http://127.0.0.1:11434/v1
```

If Ollama runs on another computer, replace `127.0.0.1` with that computer's private network IP address.

The Ollama server must be configured to accept connections from the backend computer.

Do not expose Ollama directly to the public internet.

## Running Tests

From the `Backend` directory:

```powershell
python -m pytest
```

Tests use temporary databases and mocked AI responses where appropriate.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Backend status |
| POST | `/transactions/` | Create a transaction |
| GET | `/transactions/` | Retrieve transactions |
| DELETE | `/transactions/{transaction_id}` | Delete a transaction |
| GET | `/spending/summary` | Calculate spending summary |
| GET | `/spending/compare` | Compare monthly spending |
| GET | `/recommendations/` | Generate recommendations |
| GET | `/recommendations/ai` | Generate AI explanations |

Detailed endpoint documentation is available in `docs/api-documentation.md`.

## Current Limitations

- The backend currently uses a shared local transaction database.
- Authentication and user-specific data isolation are not implemented.
- Transaction editing and income records are not yet supported.
- The frontend is not yet integrated.
- AI explanations are not automatically verified for numerical accuracy.
- The application is a development prototype and is not ready for production financial use.

## Team Development Workflow

Development takes place on feature branches.

1. Update the local `main` branch.
2. Create a feature branch.
3. Implement and test the feature.
4. Push the branch to GitHub.
5. Create a pull request.
6. Review and merge approved changes.

## Documentation

- [Core Algorithms](docs/core-algorithms.md)
- [API Documentation](docs/api-documentation.md)

## Project Status

The backend prototype currently supports transaction storage, spending analysis, monthly comparisons, financial recommendations, and AI-generated explanations.

Frontend integration, budgeting, debt planning, authentication, and deployment remain future development tasks.
