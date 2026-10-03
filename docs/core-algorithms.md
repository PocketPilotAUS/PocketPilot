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