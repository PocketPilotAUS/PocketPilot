# PocketPilot

PocketPilot is an intelligent personal finance assistant that analyzes spending, creates personalized budgets, plans debt repayment, and provides explainable financial recommendations.

## Project Overview

PocketPilot helps individuals understand their financial situation and make informed decisions about their money.

The system analyzes:
- Income
- Recurring bills
- Transactions
- Spending habits
- Debts
- Savings
- Financial goals

It then uses this information to provide:
- Spending insights
- Personalized budgets
- Debt repayment plans
- Actionable financial recommendations
- Adaptive financial planning

PocketPilot follows the workflow:

Track → Understand → Plan → Act → Improve

## Project Scope

### In Scope

- Manual financial data entry
- Transaction categorization
- Spending analysis and pattern detection
- Personalized budgeting
- Debt repayment planning
- Debt payoff strategies such as:
  - Highest-interest-first
  - Smallest-balance-first
- Savings goal tracking
- AI-generated explanations and recommendations
- Adaptive recommendations when the user's financial situation changes
- Explainable recommendations showing why an action was suggested
- User authentication and permission-based access
- Security and privacy protections for financial data

### Out of Scope

The initial version will not include:

- Direct bank account integration
- Money transfers
- Investment trading
- Cryptocurrency management
- Tax filing
- Automated bill payments
- Autonomous financial decisions

## Project Structure

```text
PocketPilot/
├── backend/
│   ├── app/
│   │   ├── algorithms/
│   │   ├── ai/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── docs/
├── data/
├── .gitignore
└── README.md
