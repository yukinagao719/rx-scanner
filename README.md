# RX Scanner

[![CI](https://github.com/yukinagao719/rx-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/yukinagao719/rx-scanner/actions/workflows/ci.yml)
[![Release](https://github.com/yukinagao719/rx-scanner/actions/workflows/release.yml/badge.svg)](https://github.com/yukinagao719/rx-scanner/actions/workflows/release.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Prescription OCR and Receipt Data Generation Application

## Overview

A desktop application designed to streamline prescription processing in medical settings. Uses image processing and OCR technology to automatically generate receipt data from prescription images. Currently features a complete medicine search and database system, with OCR functionality ready for implementation.

## Key Features

### ✅ Medicine Search Tab (Implemented)
- **High-Speed Full-Text Search**: Fast search across 12,720 medicine records
- **Japanese Language Support**: Search in Hiragana, Katakana, and Kanji
- **Incremental Search**: Real-time search results update
- **Detailed Information Display**: Product name, ingredient, specification, price, manufacturer
- **Prescription Tab Integration**: Seamless integration with prescription processing

### ✅ Database System (Implemented)
- **SQLite + FTS5**: High-performance full-text search database
- **12,720 Medicine Master Records**: Real pharmaceutical database
- **CSV Bulk Import**: Easy external data integration
- **Backup Functionality**: Data safety and integrity

### 🚧 Prescription Processing Tab (In Development)
- Prescription image loading and display
- OCR processing for text recognition
- Automatic medicine database matching
- CSV format receipt data export

## Tech Stack

- **GUI**: PySide6 (Qt6 Python bindings)
- **Database**: SQLite + FTS5 full-text search
- **Data Processing**: pandas, numpy
- **Image Processing**: OpenCV (ready)
- **OCR**: Tesseract OCR (ready)
- **Development**: Python 3.12 + Poetry
- **Code Quality**: ruff, mypy, pytest

## Quick Start

### 📥 Download Pre-built Executable (Recommended)

Download the latest release for your platform:

**[→ Download Latest Release](https://github.com/yukinagao719/rx-scanner/releases/latest)**

- **Windows**: `rx-scanner-windows-x86_64.exe` - Just double-click to run
- **macOS**: `rx-scanner-macos-x86_64` - See installation notes below

#### macOS Installation
1. Download the file
2. Right-click → "Open" → Click "Open" again

Or use Terminal:
```bash
chmod +x rx-scanner-macos-x86_64
./rx-scanner-macos-x86_64
```

---

## Development Setup

### Prerequisites

- Python 3.12
- Poetry (dependency management)
- Tesseract OCR (for OCR functionality)

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/yukinagao719/rx-scanner.git
cd rx-scanner
```

2. **Install Tesseract OCR**
```bash
# macOS
brew install tesseract tesseract-lang

# Windows
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

3. **Install Python Dependencies**
```bash
# Create Poetry environment and install dependencies
poetry install

# Activate virtual environment
poetry shell
```

4. **Database Setup**
```bash
# Import medicine data
python -m rx_scanner.database.import_csv data/medicine_list_20251001.csv
```

5. **Run Application**
```bash
python -m rx_scanner.main
```

## Usage

### Medicine Search

1. **Basic Search**: Search by medicine name or ingredient
   - Example: "Aspirin", "Loxonin"
2. **Partial Match Search**: Search with partial characters
   - Example: "Loxo" → Shows Loxonin-related medicines
3. **View Details**: Click search results for detailed information
4. **Price & Manufacturer**: Check drug prices and manufacturer info

### Database Management

```bash
# Preview data (first 10 records)
python -m rx_scanner.database.import_csv data/medicine_list_20251001.csv --preview

# Import medicine data (replaces existing data)
python -m rx_scanner.database.import_csv data/medicine_list_20251001.csv

# Direct SQLite data inspection
sqlite3 data/medicine_data.db
```

## Development Status

### ✅ Completed Features
- [x] Tab-based UI design
- [x] Medicine search functionality (FTS5 full-text search)
- [x] Medicine master database (12,720 records)
- [x] CSV bulk import functionality
- [x] Database backup functionality
- [x] Japanese language search support
- [x] Inter-tab integration

### 🚧 Planned Features
- [ ] OCR processing (Tesseract integration)
- [ ] Medicine matching logic
- [ ] Prescription image processing
- [ ] Receipt CSV export
- [ ] Enhanced error handling
- [ ] Performance optimization

## Project Structure

```
rx-scanner/
├── pyproject.toml              # Poetry configuration & dependencies
├── README.md
├── rx_scanner/                 # Main package
│   ├── main.py                # Application entry point
│   ├── ui/                    # User interface
│   │   ├── main_window.py     # Main window
│   │   ├── prescription_tab.py # Prescription processing tab
│   │   └── search_tab.py      # Medicine search tab
│   ├── database/              # Database related
│   │   ├── db_manager.py      # SQLite operations & FTS5 search
│   │   └── import_csv.py      # CSV bulk import
│   └── utils/                 # Utilities
│       └── file_utils.py      # File operations
├── tests/                     # Test files
├── resources/                 # Resource files
│   └── sample_images/         # Sample prescription images
└── data/                      # Data files
    └── medicine_list_20251001.csv  # Medicine master data (12,445 records)
```

## Database Schema

### Medicine Master Table
- **medicine_name**: Product name
- **ingredient_name**: Active ingredient name
- **specification**: Specification (dosage, form)
- **classification**: Classification (internal/external medicine)
- **price**: Drug price
- **manufacturer**: Manufacturer

### Search Features
- **FTS5 full-text search engine**
- **Japanese morphological analysis** support
- **Partial matching & fuzzy search**

## CI/CD Pipeline

This project uses GitHub Actions for automated testing and deployment:

### Continuous Integration (CI)
- **Automated Testing**: Runs on every push and pull request
- **Cross-Platform**: Tests on Windows and macOS
- **Quality Checks**: Linting (ruff), type checking (mypy), unit tests (pytest)
- **Code Coverage**: Tracked and reported

### Continuous Deployment (CD)
- **Automated Releases**: Triggered by version tags (e.g., `v0.1.0`)
- **Multi-Platform Builds**: Generates executables for Windows and macOS
- **GitHub Releases**: Automatically creates releases with binaries and release notes

**Workflow Status**: Check the [Actions tab](https://github.com/yukinagao719/rx-scanner/actions) for current build status.

## Contributing

For release procedures, see [RELEASE.md](RELEASE.md).

## License

MIT License

## Author

Yuki Nagao (dev@curifun.com)

## Disclaimer

This application is developed for portfolio and technical validation purposes. Additional features and security measures are required for actual use in medical settings.