from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
from dotenv import load_dotenv
from processing.llm_processor import LLMProcessor

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize LLM processor
llm_processor = LLMProcessor()


@app.route('/')
def index():
    """Main page with three-panel interface"""
    return render_template('index.html')


@app.route('/process-notes', methods=['POST'])
def process_notes():
    """
    Process rough notes and convert to structured HTML report
    """
    try:
        # Get rough notes from request
        data = request.get_json()
        rough_notes = data.get('notes', '')

        if not rough_notes:
            return jsonify({'error': 'No notes provided'}), 400

        # Process notes using LLM processor
        structured_html = llm_processor.process_notes_to_html(rough_notes)

        return jsonify({
            'success': True,
            'html_report': structured_html,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error(f"Error processing notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/open-mask', methods=['POST'])
def open_mask():
    """
    Open TotalSegmentator masks in 3D Slicer using SNOMED code mapping
    """
    try:
        data = request.get_json()
        snomed_code = data.get('snomed_code', '')
        filename = data.get('file', '')

        if not snomed_code and not filename:
            return jsonify({'error': 'No SNOMED code or filename provided'}), 400

        # Log the mapping for debugging
        app.logger.info(f"Opening mask: SNOMED {snomed_code} -> {filename}")

        # TODO: Implement 3D Slicer integration
        # For now, just return success with mapping info
        return jsonify({
            'success': True,
            'message': f'Would open {filename} in 3D Slicer',
            'snomed_code': snomed_code,
            'filename': filename
        })

    except Exception as e:
        app.logger.error(f"Error opening mask: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/validate-snomed-mapping', methods=['GET'])
def validate_snomed_mapping():
    """
    Debug endpoint to check SNOMED-to-file mapping completeness
    """
    try:
        # Load SNOMED data
        import pandas as pd
        snomed_df = pd.read_csv(llm_processor.snomed_csv_path)

        missing_mappings = []
        total_entries = len(snomed_df)

        for _, row in snomed_df.iterrows():
            snomed_code = str(row['SNOMED_Code'])
            snomed_term = row['SNOMED_Term']
            ts_class = row['TotalSegmentator_Class']

            # Check if this would be mappable in frontend
            if snomed_code not in ['spinal_cord', 'vertebral_body']:
                missing_mappings.append({
                    'snomed_code': snomed_code,
                    'term': snomed_term,
                    'expected_file': f"{ts_class}.nii.gz"
                })

        return jsonify({
            'total_snomed_entries': total_entries,
            'mappings_to_create': len(missing_mappings),
            'sample_missing': missing_mappings[:10],
            'csv_path': llm_processor.snomed_csv_path
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'llm_processor': llm_processor.is_configured()
    })


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('processing', exist_ok=True)

    # Run the app
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )
