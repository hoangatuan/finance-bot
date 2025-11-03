# Portfolio Management Documentation

This document provides complete instructions for AI-assisted portfolio management. The portfolio is stored in a single JSON file and should be edited directly following the guidelines below.

## File Location

**Portfolio JSON File Path:** `data/portfolio.json`

This file is created automatically on first use. Always edit this file directly when updating portfolio data.

## JSON Schema

### Complete Structure

```json
{
  "cash_balance": {
    "balance": 50000.0,
    "currency": "VND",
    "updated_at": "2024-01-15T10:30:00"
  },
  "stocks": [
    {
      "symbol": "HPG",
      "total_shares": 300,
      "avg_buy_price": 24.5,
      "buy_method": "cash",
      "sector": "Industrial",
      "note": "Long-term hold",
      "transactions": [
        {
          "id": "txn_001",
          "date": "2024-01-05T09:00:00",
          "type": "buy",
          "shares": 100,
          "price": 24.0,
          "total_cost": 2400.0,
          "buy_method": "cash",
          "note": "Initial purchase"
        },
        {
          "id": "txn_002",
          "date": "2024-01-10T10:15:00",
          "type": "sell",
          "shares": 50,
          "price": 25.5,
          "total_proceeds": 1275.0,
          "note": "Partial profit taking"
        }
      ],
      "created_at": "2024-01-05T09:00:00",
      "updated_at": "2024-01-10T10:15:00"
    }
  ],
  "metadata": {
    "version": "1.0",
    "last_updated": "2024-01-15T10:30:00",
    "total_stocks": 1
  }
}
```

## Price Format Convention

**CRITICAL:** All prices in the JSON file are stored divided by 1000.

### Examples:
- 24,500 VND → stored as `24.5`
- 50,000,000 VND → stored as `50000.0`
- 18,500 VND → stored as `18.5`

### Fields Affected:
- `cash_balance.balance`: Cash balance in storage format
- `stocks[].avg_buy_price`: Average buy price in storage format
- `stocks[].transactions[].price`: Transaction price per share in storage format
- `stocks[].transactions[].total_cost`: Total cost for buy transactions in storage format
- `stocks[].transactions[].total_proceeds`: Total proceeds for sell transactions in storage format

**When editing the JSON file, always use the storage format (divide by 1000).**

## Field Definitions

### Top Level

- `cash_balance` (object, required): Current cash balance
- `stocks` (array, required): Array of stock positions
- `metadata` (object, required): Metadata about the portfolio

### Cash Balance Object

- `balance` (float, required): Cash balance in storage format (divided by 1000)
- `currency` (string, required): Currency code (default: "VND")
- `updated_at` (string, required): ISO 8601 timestamp of last update

### Stock Object

- `symbol` (string, required): Stock symbol (e.g., "HPG", "MBB")
- `total_shares` (integer, required): Total number of shares currently held
- `avg_buy_price` (float, required): Weighted average purchase price in storage format
- `buy_method` (string, required): "cash" or "margin"
- `sector` (string, optional): Stock sector or industry (e.g., "Industrial", "Banking")
- `note` (string, optional): Personal note or comment about the stock
- `transactions` (array, required): Array of transaction history
- `created_at` (string, required): ISO 8601 timestamp of first transaction
- `updated_at` (string, required): ISO 8601 timestamp of last transaction

### Transaction Object

- `id` (string, required): Unique transaction ID (format: "txn_XXX" where XXX is sequential)
- `date` (string, required): ISO 8601 timestamp of transaction
- `type` (string, required): "buy" or "sell"
- `shares` (integer, required): Number of shares in this transaction
- `price` (float, required): Price per share in storage format (divided by 1000)
- `total_cost` (float, required for buys): Total cost in storage format (price × shares)
- `total_proceeds` (float, required for sells): Total proceeds in storage format (price × shares)
- `buy_method` (string, required for buys): "cash" or "margin"
- `note` (string, optional): Transaction note or comment

### Metadata Object

- `version` (string, required): Schema version (currently "1.0")
- `last_updated` (string, required): ISO 8601 timestamp of last portfolio update
- `total_stocks` (integer, required): Number of stocks in portfolio

## Validation Rules

### Required Fields
- All fields marked as "required" must be present
- `cash_balance`, `stocks`, and `metadata` are always required at top level

### Data Types
- `total_shares` must be non-negative integer
- `balance` and all price fields must be non-negative floats
- `symbol` must be uppercase string
- `buy_method` must be exactly "cash" or "margin"
- `transaction.type` must be exactly "buy" or "sell"

### Logical Constraints
- `total_shares` must match the sum of buy transactions minus sell transactions
- `avg_buy_price` must be calculated from transaction history
- Transaction IDs must be unique within the portfolio
- Dates must be valid ISO 8601 timestamps
- For buy transactions: `total_cost` = `price × shares`
- For sell transactions: `total_proceeds` = `price × shares`

## Common Operations

### 1. Add a New Stock Position

**Example:** Add 100 shares of HPG bought at 24,000 VND per share (cash)

```json
{
  "symbol": "HPG",
  "total_shares": 100,
  "avg_buy_price": 24.0,
  "buy_method": "cash",
  "sector": "Industrial",
  "note": "Long-term investment",
  "transactions": [
    {
      "id": "txn_001",
      "date": "2024-01-15T09:00:00",
      "type": "buy",
      "shares": 100,
      "price": 24.0,
      "total_cost": 2400.0,
      "buy_method": "cash",
      "note": "Initial purchase"
    }
  ],
  "created_at": "2024-01-15T09:00:00",
  "updated_at": "2024-01-15T09:00:00"
}
```

**Steps:**
1. Generate unique transaction ID (check existing IDs and increment)
2. Calculate `total_cost` = price × shares (in storage format)
3. Set `avg_buy_price` = price (first transaction)
4. Set `total_shares` = shares
5. Add transaction to `transactions` array
6. Set `created_at` and `updated_at` to transaction date
7. Append stock object to `stocks` array
8. Update `metadata.total_stocks`
9. Update `metadata.last_updated`

### 2. Add a Buy Transaction (Increase Position)

**Example:** Buy 50 more shares of HPG at 25,000 VND per share

**Before:**
- `total_shares`: 100
- `avg_buy_price`: 24.0
- Existing transactions: 1 buy of 100 @ 24.0

**After:**
- Calculate new `avg_buy_price`: Weighted average of (100 × 24.0 + 50 × 25.0) / 150 = 24.33
- `total_shares`: 150
- `avg_buy_price`: 24.33
- Add new transaction:
  ```json
  {
    "id": "txn_002",
    "date": "2024-01-20T10:00:00",
    "type": "buy",
    "shares": 50,
    "price": 25.0,
    "total_cost": 1250.0,
    "buy_method": "cash",
    "note": "DCA"
  }
  ```
- Update `updated_at` to transaction date

### 3. Add a Sell Transaction (Reduce Position)

**Example:** Sell 30 shares of HPG at 26,000 VND per share

**Before:**
- `total_shares`: 150
- `avg_buy_price`: 24.33

**After:**
- `total_shares`: 120 (150 - 30)
- `avg_buy_price`: 24.33 (unchanged, sell doesn't change cost basis)
- Add new transaction:
  ```json
  {
    "id": "txn_003",
    "date": "2024-01-25T14:30:00",
    "type": "sell",
    "shares": 30,
    "price": 26.0,
    "total_proceeds": 780.0,
    "note": "Partial profit taking"
  }
  ```
- Update `updated_at` to transaction date

### 4. Close a Position (Sell All Shares)

**Example:** Sell all remaining 120 shares of HPG

- Add sell transaction with `shares` equal to `total_shares`
- Set `total_shares` to 0
- Optionally remove stock from `stocks` array OR keep it with `total_shares: 0` for history
- Update `metadata.total_stocks` if removing

### 5. Update Cash Balance

**Example:** Update cash balance to 50,000,000 VND

```json
"cash_balance": {
  "balance": 50000.0,
  "currency": "VND",
  "updated_at": "2024-01-15T15:00:00"
}
```

**Steps:**
1. Convert full amount to storage format: 50,000,000 → 50000.0
2. Update `balance` field
3. Update `updated_at` timestamp

### 6. Update Stock Metadata

You can update optional fields without adding transactions:
- `sector`: Change sector classification
- `note`: Update personal notes
- `buy_method`: Change if using margin vs cash (affects stock-level method, not historical transactions)

### 7. Remove a Stock

**Steps:**
1. Find stock in `stocks` array by `symbol`
2. Remove the stock object from array
3. Update `metadata.total_stocks`
4. Update `metadata.last_updated`

## Transaction ID Generation

Transaction IDs follow the format: `txn_XXX` where XXX is a zero-padded 3-digit number.

**Rules:**
1. Start from `txn_001` for the first transaction ever
2. Check all existing transaction IDs across all stocks
3. Use the next available sequential number
4. Example: If last ID is `txn_015`, next should be `txn_016`

**Example ID Sequence:**
- First transaction: `txn_001`
- Second transaction: `txn_002`
- ...
- 99th transaction: `txn_099`
- 100th transaction: `txn_100`

## Date/Time Format

All timestamps must be in ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`

**Examples:**
- `2024-01-15T09:00:00` (January 15, 2024 at 9:00 AM)
- `2024-01-20T14:30:00` (January 20, 2024 at 2:30 PM)

Use timezone-aware if needed, but typically local time (GMT+7 for Vietnam) is acceptable.

## Error Handling

### Common Errors to Avoid

1. **Price Format Error**: Forgetting to divide by 1000
   - ❌ Wrong: `"price": 24500`
   - ✅ Correct: `"price": 24.5`

2. **Calculation Error**: Incorrect `total_cost` or `total_proceeds`
   - Always verify: `total_cost = price × shares` (in storage format)

3. **Average Price Error**: Incorrect `avg_buy_price` after multiple transactions
   - Calculate weighted average: Sum(all buy costs) / Sum(all buy shares)

4. **Share Count Mismatch**: `total_shares` doesn't match transaction history
   - Verify: `total_shares = Sum(buy shares) - Sum(sell shares)`

5. **Duplicate Transaction ID**: Reusing an existing ID
   - Always check existing IDs and use next sequential number

6. **Invalid Buy Method**: Using incorrect value
   - Must be exactly "cash" or "margin" (lowercase)

## Atomic Write Operations

When updating the JSON file programmatically:

1. Write to a temporary file first (`portfolio.json.tmp`)
2. Validate JSON syntax
3. Atomically replace original file with temp file (rename operation)
4. This prevents corruption if write is interrupted

**Note:** Manual edits don't need this, but be careful to maintain valid JSON syntax.

## Example: Complete Portfolio Update

**Scenario:** Add new stock HPG and update cash balance after purchase

```json
{
  "cash_balance": {
    "balance": 47600.0,
    "currency": "VND",
    "updated_at": "2024-01-15T09:30:00"
  },
  "stocks": [
    {
      "symbol": "HPG",
      "total_shares": 100,
      "avg_buy_price": 24.0,
      "buy_method": "cash",
      "sector": "Industrial",
      "note": "Steel industry play",
      "transactions": [
        {
          "id": "txn_001",
          "date": "2024-01-15T09:00:00",
          "type": "buy",
          "shares": 100,
          "price": 24.0,
          "total_cost": 2400.0,
          "buy_method": "cash",
          "note": "Initial purchase"
        }
      ],
      "created_at": "2024-01-15T09:00:00",
      "updated_at": "2024-01-15T09:00:00"
    }
  ],
  "metadata": {
    "version": "1.0",
    "last_updated": "2024-01-15T09:30:00",
    "total_stocks": 1
  }
}
```

**Calculation:**
- Cash before: 50,000,000 VND (50000.0 in storage)
- Purchase cost: 2,400,000 VND (2400.0 in storage)
- Cash after: 47,600,000 VND (47600.0 in storage)

## Quick Reference

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| Price | float ÷ 1000 | 24.5 | Represents 24,500 VND |
| Cash Balance | float ÷ 1000 | 50000.0 | Represents 50M VND |
| Shares | integer | 100 | Always integer |
| Transaction ID | string | "txn_001" | Sequential, unique |
| Date | ISO 8601 | "2024-01-15T09:00:00" | Timestamp |
| Buy Method | string | "cash" | Must be "cash" or "margin" |

## Best Practices

1. **Always validate JSON syntax** before saving
2. **Check transaction ID uniqueness** before adding new transactions
3. **Recalculate `avg_buy_price`** when adding buy transactions
4. **Update `total_shares`** after every transaction
5. **Keep transaction history complete** - never delete transactions, only add
6. **Update timestamps** (`updated_at`, `last_updated`) when making changes
7. **Maintain consistency** between `total_shares` and transaction history
8. **Use storage format** for all prices (divide by 1000)
9. **Document changes** in transaction notes when helpful

---

**Last Updated:** 2024-01-15
**Schema Version:** 1.0

