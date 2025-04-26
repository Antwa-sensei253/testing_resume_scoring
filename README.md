# Resume Scoring Tool

A tool that automatically scores resumes based on predefined criteria. This tool helps recruiters and hiring managers to quickly evaluate resumes and identify the most qualified candidates.

## Features

- Analyzes PDF resumes
- Provides detailed scoring based on multiple criteria
- Offers verbose output option for detailed analysis
- Easy to use command-line interface

## Installation

### Prerequisites

- Python 3.9
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Antwa-sensei253/testing_resume_scoring.git
   cd testing_resume_scoring
   ```

2. **Create a virtual environment**
   ```bash
   # For Windows
   python -m venv venv
   venv\Scripts\activate

   # For macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py ./Uploaded_Resumes/last_resume.pdf --verbose
   ```

## Usage

The basic command structure is:

```bash
python app.py <path_to_resume> [options]
```

### Parameters:

- `<path_to_resume>`: Path to the PDF resume file you want to analyze
- `--verbose`: (Optional) Display detailed analysis information

### Examples:

Analyze a single resume with basic output:
```bash
python app.py ./Uploaded_Resumes/example_resume.pdf
```

Analyze a resume with detailed output:
```bash
python app.py ./Uploaded_Resumes/example_resume.pdf --verbose
```

## Project Structure

```
testing_resume_scoring/
├── app.py                # Main application file
├── requirements.txt      # Required Python packages
└── Uploaded_Resumes/     # Directory for storing resumes
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Include your license information here]
