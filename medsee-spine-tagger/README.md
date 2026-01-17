# Report Generator

A very basic version of the report generator using Flask along with all the data and prompts which were used to generate the reports.

## Configuration

Set the following environment variables in your `.env` file or directly in your configuration:

```ini
# Flask Configuration
FLASK_SECRET_KEY='SECRET_CODE'
FLASK_ENV=development
FLASK_DEBUG=True

# Claude API Configuration  
CLAUDE_API_KEY='YOUR_CLAUDE_API_KEY'

# File Paths
SNOMED_CSV_PATH=data/snomed_spine.csv
SPINE_TEMPLATE_PATH=templates/spine_template.html

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

To run the code

```ini
python app.py
```
