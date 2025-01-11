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

## [0.2] - Enhanced Filtering and Bug Fixes

### Added
- Support for filtering by both start date and start time.
- Argument validation to ensure `start_date` and `start_time` must be provided together.

### Fixed
- Resolved an issue with invalid comparisons between `datetime64[ns]` and `date` types.
- Improved error handling for missing or incompatible arguments.

