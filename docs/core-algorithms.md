# Core Algorithms

## Spending Analysis

The spending analysis module processes user transaction data to provide basic insights into spending behavior.

The current implementation supports:

- Calculation of total spending
- Calculation of spending by category
- Calculation of each category's percentage of total spending
- Comparison of category spending between two months

### Monthly Spending Comparison

The system compares spending in each category between the current and previous month using percentage change:

Percentage Change = ((Current Spending - Previous Spending) / Previous Spending) × 100

A positive percentage indicates an increase in spending, while a negative percentage indicates a decrease.

### Testing

Unit tests are included to verify the spending calculations using pytest.

## Recommendation Engine

The recommendation engine analyzes percentage changes in
spending categories and generates financial insights.

### Recommendation Rules

- Spending increase of 20% or more:
  Generate a high-priority recommendation.
- Spending decrease of 20% or more:
  Generate a low-priority informational message.
- Changes between -20% and +20%:
  No recommendation is generated.

The 20% threshold is currently a development assumption
and is subject to review by the Finance team member.

### AI Explanation System

PocketPilot uses a locally hosted Qwen3 4B model through
Ollama to generate natural-language explanations.

The AI model runs on a separate desktop computer and
communicates with the FastAPI backend through a private
network connection.

The recommendation engine calculates the financial
information before sending it to the AI model.

The AI model is instructed to:
- Use only the supplied financial information.
- Avoid inventing amounts, percentages, or balances.
- Avoid unsupported assumptions about the user.
- Provide short and understandable explanations.

### Current Limitations

- The AI integration currently uses sample financial data.
- The 20% recommendation threshold is provisional.
- The AI explanations are not yet automatically verified
  against the original financial calculations.
- The Ollama server must be running and reachable.
- The AI system is not yet connected to the frontend.