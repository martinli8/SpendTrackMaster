# Spend Tracker Dashboard - Comprehensive Financial Management System

## Overview

This is a Streamlit-based personal finance application that provides comprehensive spend tracking, budgeting, and financial analysis capabilities. The application allows users to import bank statements, manage recurring expenses, track travel budgets, and categorize transactions for detailed financial insights.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application framework
- **UI Components**: Multi-page application with navigation through Streamlit pages
- **Visualization**: Plotly Express and Plotly Graph Objects for interactive charts and graphs
- **Layout**: Wide layout configuration with responsive columns and expandable sections

### Backend Architecture
- **Database**: SQLite for local data persistence
- **Data Processing**: Pandas for data manipulation and analysis
- **File Processing**: Support for CSV and Excel file imports
- **Application Structure**: Modular design with separate files for database operations, utilities, and page components

### Database Schema
- **transactions**: Stores imported bank transaction data with categorization
- **recurring_expenses**: Manages fixed costs and recurring payments
- **travel_budget**: Handles travel fund allocations and expenses (implied from code structure)

## Key Components

### Core Application (app.py)
- Main dashboard with financial metrics and overview
- Date range selection for filtering data
- Travel budget balance tracking
- Monthly expense summaries

### Database Layer (database.py)
- SQLite database initialization and connection management
- Transaction and recurring expense data models
- Database query functions for retrieving financial data
- Travel budget balance calculations

### Utility Functions (utils.py)
- Date and time formatting utilities
- Currency calculation and prorated amount functions
- Bank CSV/Excel file parsing capabilities
- Data validation and formatting helpers

### Page Components
1. **Upload Statements**: Import bank CSV/Excel files
2. **Recurring Expenses**: Manage fixed costs and subscriptions
3. **Travel Budget**: Dedicated travel fund management
4. **Categorize Transactions**: Review and categorize imported transactions

## Data Flow

1. **Data Import**: Users upload bank statements (CSV/Excel) through the upload interface
2. **Transaction Processing**: Files are parsed and validated, then stored in the transactions table
3. **Categorization**: Users can review and categorize imported transactions
4. **Recurring Expenses**: Fixed costs are managed separately and factored into budget calculations
5. **Travel Budget**: Special budget category with allocation and expense tracking
6. **Dashboard Display**: Aggregated data is presented through various charts and metrics

## External Dependencies

### Python Libraries
- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualization library
- **sqlite3**: Database connectivity (built-in Python library)
- **datetime**: Date and time handling
- **calendar**: Calendar-related utilities

### File Format Support
- CSV files from bank exports
- Excel files (.xlsx, .xls) from financial institutions
- UTF-8 encoded text files

## Deployment Strategy

### Local Development
- SQLite database for local data storage
- Streamlit development server for testing
- File-based configuration and data persistence

### Production Considerations
- The application is designed for single-user local deployment
- Database file (spend_tracker.db) stores all financial data locally
- No external API dependencies for core functionality
- Suitable for personal finance management on local machines

### Key Architectural Decisions
1. **SQLite Choice**: Chosen for simplicity and zero-configuration setup, ideal for personal finance tracking
2. **Streamlit Framework**: Provides rapid development and built-in UI components for data applications
3. **Modular Structure**: Separated concerns with distinct files for database, utilities, and page components
4. **File-based Imports**: Direct CSV/Excel import eliminates need for bank API integrations
5. **Local Storage**: All data remains on user's machine for privacy and security