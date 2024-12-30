# Changelog

All notable changes to this project will be documented in this file.

## [0.1] - Initial Release

### Added
- **Script Features**:
  - Filter and aggregate Taiwan Futures Exchange data based on product code and expiry month.
  - Command-line interface for specifying input file, product code, expiry month, and output file.
- **Core Functionality**:
  - Load data from CSV files.
  - Preprocess data by trimming whitespace and formatting date and time fields.
  - Filter data based on user-specified criteria.
  - Aggregate data to compute:
    - Open price
    - Close price
    - High price
    - Low price
  - Save the filtered and aggregated data to a new CSV file.
- **Error Handling**:
  - Missing files.
  - Empty filters.
  - Invalid arguments.

### Version Summary
This version provides the core functionality for data filtering and aggregation, allowing users to process financial transaction data effectively. The script supports robust error handling and customizable output paths.

