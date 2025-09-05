# RX Scanner

Prescription OCR and Receipt Data Generation Application

## Overview

A desktop application designed to streamline prescription processing in medical settings. Utilizes image processing and OCR technology to automatically generate receipt data from prescription images.

## Key Features

### Prescription Processing Tab (Main Function)
- Load and display prescription images
- OCR processing for text recognition
- Automatic matching with medicine master database
- Export receipt data to CSV format

### Medicine Search Tab (Sub Function)
- High-speed search across entire medicine master database
- Incremental search support
- Display detailed medicine information
- Integration with prescription processing tab

## Tech Stack

- **Framework**: PySide6 (Qt6 Python bindings)
- **Image Processing**: OpenCV
- **OCR**: Tesseract OCR
- **Database**: SQLite + SQLAlchemy
- **Data Processing**: pandas, numpy
- **Development**: Python 3.12 + Poetry

## Setup

### Prerequisites

- Python 3.12
- Poetry (dependency management)
- Tesseract OCR

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/rx-scanner.git
cd rx-scanner
```

2. **Install Tesseract OCR**
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

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

4. **Run Application**
```bash
python rx_scanner/main.py
```

## Usage

### Basic Workflow

1. **Load Prescription Image**: Click "Open Image" to select prescription image
2. **Run OCR**: Click "Run OCR" to start text recognition
3. **Review & Edit**: Manually correct OCR results if needed
4. **Match Medicines**: Click "Match Medicines" to cross-reference with medicine database
5. **Export CSV**: Click "Export CSV" to save receipt data

### Medicine Search Function

- Use "Medicine Search" tab for independent medicine lookup
- Incremental search starts with 2+ characters
- Select search results to view detailed information
- Click "Add to Prescription Tab" for integration

## Development Status

### ✅ Implemented Features
- [x] Tab-based UI design
- [x] Image loading and display
- [x] Basic OCR processing framework
- [x] Medicine search UI (with dummy data)
- [x] Inter-tab integration
- [x] Basic CSV export functionality

### 🚧 Planned Features
- [ ] Actual OCR processing (Tesseract integration)
- [ ] Medicine master database construction
- [ ] Medicine matching logic implementation
- [ ] Enhanced error handling
- [ ] Performance optimization

## Project Structure

```
rx-scanner/
├── pyproject.toml          # Poetry configuration and dependencies
├── README.md
├── rx_scanner/             # Main package
│   ├── main.py            # Application entry point
│   ├── ui/                # User interface
│   │   ├── main_window.py # Main window
│   │   ├── prescription_tab.py # Prescription processing tab
│   │   └── search_tab.py  # Medicine search tab
│   ├── database/          # Database related
│   │   ├── db_manager.py  # Database operations
│   │   └── setup_db.py    # Database initialization
│   └── utils/             # Utilities
│       └── file_utils.py  # File operations
├── tests/                 # Test files
├── resources/             # Resource files
│   └── sample_images/     # Sample prescription images
└── data/                  # Data files
    └── medicine_master.csv # Medicine master data
```

## License

MIT License

## Author

Yuki Nagao (dev@curifun.com)

## Disclaimer

This application is developed for portfolio and technical validation purposes. Additional features and security measures are required for actual use in medical settings.