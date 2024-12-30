# Data Filtering and Aggregation Tool

This repository provides a Python script for filtering and aggregating Taiwan Futures Exchange data based on specified criteria. The tool allows users to process large datasets efficiently by filtering based on product codes and expiry months, and by aggregating transaction data.

## Features

- Load data from CSV files.
- Remove unnecessary whitespace and convert dates and times to proper formats.
- Filter data based on specified product codes and expiry months.
- Aggregate data to compute:
  - Open price
  - Close price
  - High price
  - Low price
- Save the processed data to a new CSV file.

## Prerequisites

- Python 3.8 or higher
- Required Python packages:
  - pandas

You can install the dependencies using:

```bash
pip install pandas
```

## Usage

### Command-Line Arguments

The script uses the `argparse` library to parse command-line arguments. The following arguments are supported:

| Argument         | Abbreviation | Required | Description                                                    |
| ---------------- | ------------ | -------- | -------------------------------------------------------------- |
| `--file_path`    | `-f`         | Yes      | Path to the input CSV file.                                    |
| `--product_code` | `-p`         | Yes      | Product code to filter, e.g., `MTX`.                           |
| `--expiry_month` | `-e`         | Yes      | Expiry month to filter, e.g., `202501`.                        |
| `--output_path`  | `-o`         | No       | Path to save the filtered data (default: `filtered_data.csv`). |

### Example

To run the script with a sample dataset:

```bash
python filter_data_script.py -f input.csv -p MTX -e 202501 -o output.csv
```

This will:

1. Load the data from `input.csv`.
2. Filter the rows where the product code is `MTX` and the expiry month is `202501`.
3. Aggregate the data based on transaction times.
4. Save the filtered and aggregated data to `output.csv`.

## Error Handling

- If required arguments are missing, the script will show an error message and suggest using `-h` for help.
- If the input file is not found, a descriptive error message will be displayed.
- If no data matches the filter criteria, a warning will be shown, and no file will be saved.

## File Structure

- **`filter_data_script.py`**: The main script for filtering and aggregating data.
- **`README.md`**: Documentation for the tool (this file).

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request with improvements or new features.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

