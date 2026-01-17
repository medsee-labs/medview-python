import os
import pandas as pd
import anthropic
from dotenv import load_dotenv
import re
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()


class LLMProcessor:
    """
    Handles all LLM-related processing for spine report generation
    """

    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        self.snomed_csv_path = os.getenv(
            'SNOMED_CSV_PATH', 'data/snomed_spine.csv')
        self.template_path = os.getenv(
            'SPINE_TEMPLATE_PATH', 'templates/spine_template.html')

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: Claude API key not found in environment variables")

    def is_configured(self):
        """Check if the processor is properly configured"""
        return {
            'api_key_present': bool(self.api_key),
            'snomed_csv_exists': os.path.exists(self.snomed_csv_path),
            'template_exists': os.path.exists(self.template_path)
        }

    def load_snomed_data(self):
        """Load and format SNOMED data for Claude reference"""
        try:
            if not os.path.exists(self.snomed_csv_path):
                raise FileNotFoundError(
                    f"SNOMED CSV not found: {self.snomed_csv_path}")

            snomed_df = pd.read_csv(self.snomed_csv_path)
            return self._format_snomed_reference(snomed_df)

        except Exception as e:
            print(f"Error loading SNOMED data: {e}")
            return "SNOMED data unavailable"

    def _format_snomed_reference(self, snomed_df):
        """Format SNOMED data for Claude consumption"""
        reference = "SPINE ANATOMY SNOMED REFERENCE:\n"

        # Group by category for better organization
        if 'Category' in snomed_df.columns:
            categories = snomed_df.groupby('Category')

            for category, group in categories:
                reference += f"\n{category.upper()}:\n"
                for _, row in group.iterrows():
                    reference += f"- {row['SNOMED_Term']} → {row['SNOMED_Code']} → {row['TotalSegmentator_Class']}\n"
        else:
            # Fallback if no Category column
            for _, row in snomed_df.iterrows():
                reference += f"- {row.get('SNOMED_Term', 'Unknown')} → {row.get('SNOMED_Code', 'Unknown')}\n"

        return reference

    def load_html_template(self):
        """Load the HTML template"""
        try:
            if not os.path.exists(self.template_path):
                raise FileNotFoundError(
                    f"Template not found: {self.template_path}")

            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            print(f"Error loading template: {e}")
            return "<html><body><h1>Template Error</h1><p>Could not load spine template</p></body></html>"

    def create_claude_prompt(self, rough_notes, html_template, snomed_reference):
        """Create the comprehensive prompt for Claude"""

        prompt = f"""
        You are a medical report generator specializing in spine radiology reports. Convert the rough radiologist notes into a structured, professional HTML spine report.

        CRITICAL ANATOMICAL TAGGING RULES:
        1. CONTEXT-BASED CLASSIFICATION: For each anatomical mention, read the ENTIRE sentence (and next sentence if needed) to determine classification:
        
        DISC LEVEL indicators (use SNOMED codes from reference):
        - Any mention of: disc, disc space, disc height, protrusion, bulge, extrusion, herniation, degeneration, desiccation, annular tear, annular fissure, disc material, IVDD
        - Example: "C5-C6 disc protrusion" → <span class="disc-level-term" onclick="openMask('73959003')">C5-C6</span>
        
        INDIVIDUAL VERTEBRA indicators (use SNOMED codes from reference):
        - Any mention of: vertebra, vertebral body, fracture, compression, height, marrow signal, alignment, osteophyte, sclerosis, intact, unremarkable, normal
        - Example: "C6 vertebra shows compression" → <span class="cervical-vertebra" onclick="openMask('36054005')">C6</span>
        
        2. NO DOUBLE TAGGING: If you see "C5-C6" and context indicates disc pathology, tag ONLY "C5-C6" as disc level. Do NOT also tag "C5" and "C6" individually.

        3. ANATOMICAL TERM NORMALIZATION:
        - "5th cervical vertebra" → normalize to "C5"
        - "first lumbar" → normalize to "L1"  
        - "T12-L1 junction" → normalize to "T12-L1"
        - Always use standard notation (C1-C7, T1-T12, L1-L5, S1, sacrum)

        4. DYNAMIC SNOMED MAPPING: Find the exact SNOMED code from reference data:
        - Look up anatomical term in SNOMED reference data
        - Use the corresponding SNOMED_Code in onclick attribute
        - Example: C3 vertebra → find "C3 Vertebra" → use SNOMED code "1.13E+08"
        - Example: L4-L5 disc → find "Intervertebral disc, L4-L5" → use SNOMED code "84020006"
        
        5. SPECIAL CASES:
        - "Sacrum" or "sacral" → <span class="lumbar-vertebra" onclick="openMask('54735007')">sacrum</span>
        - "Spinal cord" → <span class="spinal-structure" onclick="openMask('spinal_cord')">spinal cord</span>
        - "Vertebral body" (general) → <span class="spinal-structure" onclick="openMask('vertebral_body')">vertebral body</span>

        6. "When you see pathological terms without explicit levels (facet arthropathy, disc degeneration, etc.), look for nearby anatomical references in the same sentence or paragraph to determine the most likely location. Only tag if location can be reasonably inferred from context."

        7. CONTEXTUAL INFERENCE RULES:
        When pathological terms lack explicit anatomical levels, use contextual clues:
        - Look for nearby level references in same paragraph
        - Consider typical anatomical locations for pathology
        - For lumbar spine context: facet arthropathy, ligamentum flavum thickening typically at L4-L5, L5-S1
        - For cervical context: uncovertebral joint changes typically C3-C7
        - Only infer if context strongly suggests location
        - Example: "lower back pain... facet arthropathy" → infer lumbar levels 

        TEMPLATE SECTION HANDLING:
        1. DYNAMIC SECTION VISIBILITY: Based on what's mentioned in the rough notes:
           - If CERVICAL findings (C1-C7) mentioned → [CERVICAL_DISPLAY] = "block", populate [CERVICAL_FINDINGS]
           - If NO cervical findings → [CERVICAL_DISPLAY] = "none"
           
           - If THORACIC findings (T1-T12) mentioned → [THORACIC_DISPLAY] = "block", populate [THORACIC_FINDINGS]  
           - If NO thoracic findings → [THORACIC_DISPLAY] = "none"
           
           - If LUMBAR findings (L1-L5, S1) mentioned → [LUMBAR_DISPLAY] = "block", populate [LUMBAR_FINDINGS]
           - If NO lumbar findings → [LUMBAR_DISPLAY] = "none"

        2. ALTERNATIVE APPROACH - NO FINDINGS MESSAGE:
           Instead of hiding sections, you can show informative messages:
           - If no cervical findings: [CERVICAL_FINDINGS] = "<p class='no-findings'>No cervical spine findings reported.</p>"
           - If no thoracic findings: [THORACIC_FINDINGS] = "<p class='no-findings'>No thoracic spine findings reported.</p>"
           - If no lumbar findings: [LUMBAR_FINDINGS] = "<p class='no-findings'>No lumbar spine findings reported.</p>"

        3. TEMPLATE PLACEHOLDERS TO FILL:
           - [STUDY_TYPE]: Determine from notes (e.g., "MRI CERVICAL SPINE", "MRI LUMBAR SPINE", "MRI COMPLETE SPINE")
           - [TECHNIQUE_DETAILS]: Extract imaging parameters mentioned
           - [GENERAL_FINDINGS]: Overall alignment, vertebral body overview (if mentioned)
           - [CERVICAL_DISPLAY]: "block" or "none" 
           - [CERVICAL_FINDINGS]: Cervical content OR no-findings message
           - [THORACIC_DISPLAY]: "block" or "none"
           - [THORACIC_FINDINGS]: Thoracic content OR no-findings message  
           - [LUMBAR_DISPLAY]: "block" or "none"
           - [LUMBAR_FINDINGS]: Lumbar content OR no-findings message
           - [ADDITIONAL_FINDINGS]: Spinal cord, conus, paraspinal tissues
           - [IMPRESSION_FINDINGS]: Summary and key conclusions

        4. CHOOSE YOUR APPROACH:
           - Option A: Hide empty sections (style="display: none")
           - Option B: Show "No [region] findings reported" message
           
           Use Option B (show informative messages) for better user experience.

        EXAMPLE CORRECT TAGGING USING SNOMED CODES:
        Input: "C5-C6 disc protrusion with C6 vertebral body compression."
        Template Output:
        - Find "Intervertebral disc, C5-C6" in reference → SNOMED code "73959003"
        - Find "C6 Vertebra" in reference → SNOMED code "36054005"  
        - Output: "<span class='disc-level-term' onclick='openMask('73959003')'>C5-C6</span> disc protrusion with <span class='cervical-vertebra' onclick='openMask('36054005')'>C6</span> vertebral body compression."

        SNOMED REFERENCE DATA:
        {snomed_reference}

        HTML TEMPLATE TO POPULATE:
        {html_template}

        ROUGH RADIOLOGIST NOTES:
        {rough_notes}

        RETURN: Complete populated HTML document only. No explanations, no markdown formatting.
        """

        return prompt

    def call_claude_api(self, prompt):
        """Call Claude API with error handling"""
        if not self.client:
            return "<html><body><h1>API Error</h1><p>Claude API not configured</p></body></html>"

        try:
            message = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return message.content[0].text

        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"<html><body><h1>API Error</h1><p>Error generating report: {str(e)}</p></body></html>"

    def process_notes_to_html(self, rough_notes):
        """Main method: Convert rough notes to structured HTML report with SNOMED validation"""
        snomed_reference = self.load_snomed_data()
        html_template = self.load_html_template()

        prompt = self.create_claude_prompt(
            rough_notes, html_template, snomed_reference)
        structured_html = self.call_claude_api(prompt)

        # Validate SNOMED tagging
        debug_info = self.validate_snomed_tagging(structured_html, rough_notes)

        print("SNOMED TAGGING VALIDATION")
        print(
            f"Total tagged terms: {debug_info['statistics']['total_tagged_terms']}")
        print(
            f"Validation errors: {debug_info['statistics']['validation_errors']}")

        if debug_info['validation_errors']:
            print("VALIDATION ERRORS:")
            for error in debug_info['validation_errors']:
                print(f"  {error}")

        print("SNOMED TAGGING RESULTS:")
        for term_info in debug_info['tagged_terms']:
            status = "VALID" if term_info['is_valid'] else "INVALID"
            print(
                f"  {status}: '{term_info['term']}' -> {term_info['snomed_code']}")

        return structured_html

    def validate_input(self, rough_notes):
        """Validate input notes"""
        if not rough_notes or not rough_notes.strip():
            raise ValueError("Empty or invalid notes provided")

        if len(rough_notes) > 10000:  # Reasonable limit
            raise ValueError("Notes too long (max 10,000 characters)")

        return True

    def validate_snomed_tagging(self, generated_html, rough_notes):
        """Validate that LLM used correct SNOMED codes"""
        debug_info = {
            'tagged_terms': [],
            'validation_errors': [],
            'statistics': {}
        }

        try:
            soup = BeautifulSoup(generated_html, 'html.parser')
            anatomical_spans = soup.find_all('span', class_=[
                                             'cervical-vertebra', 'thoracic-vertebra', 'lumbar-vertebra', 'disc-level-term', 'spinal-structure'])

            snomed_df = pd.read_csv(self.snomed_csv_path)

            for span in anatomical_spans:
                term_text = span.get_text().strip()
                onclick_attr = span.get('onclick', '')
                css_class = ' '.join(span.get('class', []))

                # Extract SNOMED code from onclick
                snomed_match = re.search(
                    r"openMask\('([^']+)'\)", onclick_attr)
                used_snomed = snomed_match.group(
                    1) if snomed_match else 'NO_SNOMED'

                # Validate SNOMED code
                is_valid = self.validate_snomed_code(
                    term_text, used_snomed, snomed_df)

                debug_info['tagged_terms'].append({
                    'term': term_text,
                    'css_class': css_class,
                    'snomed_code': used_snomed,
                    'is_valid': is_valid
                })

                if not is_valid:
                    debug_info['validation_errors'].append(
                        f"Invalid SNOMED: {term_text} -> {used_snomed}")

            debug_info['statistics'] = {
                'total_tagged_terms': len(anatomical_spans),
                'validation_errors': len(debug_info['validation_errors'])
            }

        except Exception as e:
            debug_info['validation_errors'].append(
                f"Validation error: {str(e)}")

        return debug_info

    def validate_snomed_code(self, term_text, snomed_code, snomed_df):
        """Check if SNOMED code matches the anatomical term"""
        # Find matching entries in SNOMED data
        matching_rows = snomed_df[
            (snomed_df['SNOMED_Term'].str.contains(term_text, case=False, na=False)) |
            (snomed_df['SNOMED_Code'].astype(str) == str(snomed_code))
        ]

        return len(matching_rows) > 0
