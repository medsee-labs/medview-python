// MedSee.ai Spine Report Generator - Frontend JavaScript

// SNOMED Code to File Mapping Dictionary
const SNOMED_TO_FILE_MAPPING = {
	// Cervical Vertebrae
	14806007: "vertebrae_C1.nii.gz",
	39976000: "vertebrae_C2.nii.gz",
	113200001: "vertebrae_C3.nii.gz",
	5329002: "vertebrae_C4.nii.gz",
	36978003: "vertebrae_C5.nii.gz",
	36054005: "vertebrae_C6.nii.gz",
	87391001: "vertebrae_C7.nii.gz",

	// Thoracic Vertebrae
	64864005: "vertebrae_T1.nii.gz",
	53733008: "vertebrae_T2.nii.gz",
	1626008: "vertebrae_T3.nii.gz",
	73071006: "vertebrae_T4.nii.gz",
	56401006: "vertebrae_T5.nii.gz",
	45296009: "vertebrae_T6.nii.gz",
	62487009: "vertebrae_T7.nii.gz",
	11068009: "vertebrae_T8.nii.gz",
	82687006: "vertebrae_T9.nii.gz",
	7610001: "vertebrae_T10.nii.gz",
	12989004: "vertebrae_T11.nii.gz",
	23215003: "vertebrae_T12.nii.gz",

	// Lumbar Vertebrae
	66794005: "vertebrae_L1.nii.gz",
	14293000: "vertebrae_L2.nii.gz",
	36470004: "vertebrae_L3.nii.gz",
	11994002: "vertebrae_L4.nii.gz",
	49668003: "vertebrae_L5.nii.gz",

	// Sacral/Coccygeal Vertebrae
	65985001: "vertebrae_S1.nii.gz",
	52605009: "vertebrae_Co1.nii.gz",
	54735007: "vertebrae_sacrum.nii.gz",
	72153006: "vertebrae_coccyx.nii.gz",

	// Intervertebral Discs
	1078209008: "disc_C2_C3.nii.gz",
	58820006: "disc_C3_C4.nii.gz",
	49400002: "disc_C4_C5.nii.gz",
	73959003: "disc_C5_C6.nii.gz",
	75095006: "disc_C6_C7.nii.gz",
	37414007: "disc_C7_T1.nii.gz",
	40908007: "disc_T1_T2.nii.gz",
	6004007: "disc_T2_T3.nii.gz",
	2620004: "disc_T3_T4.nii.gz",
	82965004: "disc_T4_T5.nii.gz",
	72692000: "disc_T5_T6.nii.gz",
	74401007: "disc_T6_T7.nii.gz",
	28693002: "disc_T7_T8.nii.gz",
	9188009: "disc_T8_T9.nii.gz",
	113200001: "disc_T9_T10.nii.gz",
	34959001: "disc_T10_T11.nii.gz",
	1537001: "disc_T11_T12.nii.gz",
	76206002: "disc_T12_L1.nii.gz",
	80064006: "disc_L1_L2.nii.gz",
	67459009: "disc_L2_L3.nii.gz",
	62551000: "disc_L3_L4.nii.gz",
	84020006: "disc_L4_L5.nii.gz",
	75782005: "disc_L5_S1.nii.gz",

	// Special structures
	spinal_cord: "spinal_cord.nii.gz",
	vertebral_body: "vertebral_body.nii.gz",
};

class SpineReportGenerator {
	constructor() {
		this.selectedTerms = new Set();
		this.isProcessing = false;
		this.init();
	}

	init() {
		this.bindEvents();
		this.updateInputStats();
		this.checkServerHealth();
	}

	bindEvents() {
		// Button events
		document
			.getElementById("process-btn")
			.addEventListener("click", () => this.processNotes());
		document
			.getElementById("clear-btn")
			.addEventListener("click", () => this.clearNotes());
		document
			.getElementById("export-btn")
			.addEventListener("click", () => this.exportReport());
		document
			.getElementById("slicer-btn")
			.addEventListener("click", () => this.openSlicer());

		// Input events
		const notesInput = document.getElementById("notes-input");
		notesInput.addEventListener("input", () => this.updateInputStats());
		notesInput.addEventListener("keydown", (e) => this.handleKeyShortcuts(e));

		// Window events
		window.addEventListener("beforeunload", (e) => this.handlePageUnload(e));
	}

	// Input Statistics
	updateInputStats() {
		const notesInput = document.getElementById("notes-input");
		const text = notesInput.value;

		const charCount = text.length;
		const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

		document.getElementById(
			"char-count"
		).textContent = `${charCount} characters`;
		document.getElementById("word-count").textContent = `${wordCount} words`;

		// Enable/disable process button
		const processBtn = document.getElementById("process-btn");
		processBtn.disabled = charCount === 0 || this.isProcessing;
	}

	// Clear Notes
	clearNotes() {
		if (confirm("Clear all notes? This action cannot be undone.")) {
			document.getElementById("notes-input").value = "";
			this.updateInputStats();
			this.showToast("Notes cleared", "success");
		}
	}

	// Main Processing Function
	async processNotes() {
		const notesInput = document.getElementById("notes-input");
		const notes = notesInput.value.trim();

		if (!notes) {
			this.showToast("Please enter some notes first", "error");
			return;
		}

		this.setProcessingState(true);

		try {
			const response = await fetch("/process-notes", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					notes: notes,
					timestamp: new Date().toISOString(),
				}),
			});

			const data = await response.json();

			if (data.success) {
				this.displayReport(data.html_report);
				this.showToast("Report generated successfully!", "success");
				document.getElementById("export-btn").disabled = false;
			} else {
				throw new Error(data.error || "Unknown error occurred");
			}
		} catch (error) {
			console.error("Error processing notes:", error);
			this.showToast(`Error: ${error.message}`, "error");
			this.displayError(error.message);
		} finally {
			this.setProcessingState(false);
		}
	}

	// Display Generated Report
	displayReport(htmlContent) {
		const reportDisplay = document.getElementById("report-display");
		reportDisplay.innerHTML = `<div class="report-content">${htmlContent}</div>`;

		// Bind click events to anatomical terms
		this.bindAnatomicalTermEvents();

		// Update status
		this.updateProcessingStatus("Report generated");
	}

	// Display Error Message
	displayError(errorMessage) {
		const reportDisplay = document.getElementById("report-display");
		reportDisplay.innerHTML = `
            <div class="error-message">
                <h3>⚠️ Error Generating Report</h3>
                <p>${errorMessage}</p>
                <p>Please check your notes and try again.</p>
            </div>
        `;
	}

	// Bind Events to Anatomical Terms
	bindAnatomicalTermEvents() {
		const anatomicalTerms = document.querySelectorAll(
			".cervical-vertebra, .thoracic-vertebra, .lumbar-vertebra, .disc-level-term, .spinal-structure, .pathology-term"
		);

		anatomicalTerms.forEach((term) => {
			term.addEventListener("click", (e) => this.handleAnatomicalTermClick(e));
		});
	}

	// Handle Anatomical Term Clicks
	handleAnatomicalTermClick(event) {
		const term = event.target;
		const termText = term.textContent;
		const fileName = term.getAttribute("onclick")?.match(/'([^']+)'/)?.[1];

		// Visual feedback
		term.classList.add("clicked");
		setTimeout(() => term.classList.remove("clicked"), 200);

		// Add to selected terms
		this.selectedTerms.add({
			text: termText,
			file: fileName,
			type: term.className,
		});

		this.updateSelectedTermsDisplay();
		this.showToast(`Selected: ${termText}`, "success");

		// If file specified, prepare for 3D visualization
		if (fileName) {
			this.prepareVisualization(fileName, termText);
		}
	}

	// Update Selected Terms Display
	updateSelectedTermsDisplay() {
		const selectedTermsDiv = document.getElementById("selected-terms");
		const termsList = document.getElementById("terms-list");

		if (this.selectedTerms.size === 0) {
			selectedTermsDiv.style.display = "none";
			return;
		}

		selectedTermsDiv.style.display = "block";
		termsList.innerHTML = "";

		this.selectedTerms.forEach((term) => {
			const termTag = document.createElement("span");
			termTag.className = "term-tag";
			termTag.textContent = term.text;
			termTag.title = `File: ${term.file}`;
			termsList.appendChild(termTag);
		});

		// Enable 3D Slicer button
		document.getElementById("slicer-btn").disabled = false;
	}

	// Prepare for 3D Visualization
	prepareVisualization(fileName, snomedCode) {
		console.log(
			`Preparing visualization for SNOMED: ${snomedCode} -> ${fileName}`
		);
		this.updateProcessingStatus(
			`Selected: ${fileName.replace(".nii.gz", "").replace("_", " ")}`
		);

		// Add to selected terms with both SNOMED and filename
		this.selectedTerms.add({
			snomed_code: snomedCode,
			file: fileName,
			display_name: fileName.replace(".nii.gz", "").replace("_", " "),
		});

		this.updateSelectedTermsDisplay();
	}

	// Open 3D Slicer
	async openSlicer() {
		if (this.selectedTerms.size === 0) {
			this.showToast("No anatomical terms selected", "error");
			return;
		}

		const filesToOpen = Array.from(this.selectedTerms).map((term) => term.file);

		try {
			const response = await fetch("/open-mask", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					files: filesToOpen,
					terms: Array.from(this.selectedTerms),
				}),
			});

			const data = await response.json();

			if (data.success) {
				this.showToast("Opening 3D Slicer...", "success");
			} else {
				throw new Error(data.error || "Failed to open 3D Slicer");
			}
		} catch (error) {
			console.error("Error opening 3D Slicer:", error);
			this.showToast(`Error: ${error.message}`, "error");
		}
	}

	// Export Report
	exportReport() {
		const reportContent = document.getElementById("report-display").innerHTML;

		if (!reportContent || reportContent.includes("placeholder-message")) {
			this.showToast("No report to export", "error");
			return;
		}

		// Create and download HTML file
		const blob = new Blob([reportContent], { type: "text/html" });
		const url = URL.createObjectURL(blob);

		const a = document.createElement("a");
		a.href = url;
		a.download = `spine-report-${new Date().toISOString().split("T")[0]}.html`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);

		this.showToast("Report exported successfully!", "success");
	}

	// Processing State Management
	setProcessingState(isProcessing) {
		this.isProcessing = isProcessing;
		const loadingOverlay = document.getElementById("loading-overlay");
		const processBtn = document.getElementById("process-btn");
		const statusDot = document.getElementById("status-dot");
		const statusText = document.getElementById("status-text");

		if (isProcessing) {
			loadingOverlay.style.display = "flex";
			processBtn.disabled = true;
			processBtn.textContent = "Processing...";
			statusDot.style.backgroundColor = "#ed8936";
			statusText.textContent = "Processing";
			this.updateProcessingStatus("Generating report...");
		} else {
			loadingOverlay.style.display = "none";
			processBtn.disabled = false;
			processBtn.textContent = "Generate Report";
			statusDot.style.backgroundColor = "#48bb78";
			statusText.textContent = "Ready";
		}
	}

	// Update Processing Status
	updateProcessingStatus(message) {
		document.getElementById("processing-status").textContent = message;
	}

	// Show Toast Notifications
	showToast(message, type = "info", duration = 3000) {
		const toastContainer = document.getElementById("toast-container");

		const toast = document.createElement("div");
		toast.className = `toast ${type}`;
		toast.textContent = message;

		toastContainer.appendChild(toast);

		setTimeout(() => {
			if (toast.parentNode) {
				toast.parentNode.removeChild(toast);
			}
		}, duration);
	}

	// Keyboard Shortcuts
	handleKeyShortcuts(event) {
		if (event.ctrlKey || event.metaKey) {
			switch (event.key) {
				case "Enter":
					event.preventDefault();
					if (!this.isProcessing) {
						this.processNotes();
					}
					break;
				case "k":
					event.preventDefault();
					this.clearNotes();
					break;
				case "s":
					event.preventDefault();
					this.exportReport();
					break;
			}
		}
	}

	// Page Unload Handler
	handlePageUnload(event) {
		if (this.isProcessing) {
			event.preventDefault();
			event.returnValue =
				"Report generation is in progress. Are you sure you want to leave?";
			return event.returnValue;
		}
	}

	// Server Health Check
	async checkServerHealth() {
		try {
			const response = await fetch("/health");
			const data = await response.json();

			if (data.status === "healthy") {
				this.updateProcessingStatus("Connected to server");
			} else {
				this.updateProcessingStatus("Server issues detected");
			}
		} catch (error) {
			console.error("Health check failed:", error);
			this.updateProcessingStatus("Server connection failed");
			this.showToast("Server connection issues detected", "error");
		}
	}
}

// Global function for anatomical term clicks (called by generated HTML)
function openMask(snomedCode) {
	console.log(`Opening mask for SNOMED code: ${snomedCode}`);

	// Look up filename from SNOMED code
	const fileName = SNOMED_TO_FILE_MAPPING[snomedCode];

	if (fileName) {
		console.log(`Mapped to file: ${fileName}`);

		if (window.spineReportGenerator) {
			window.spineReportGenerator.prepareVisualization(fileName, snomedCode);
		}

		// Send to backend to open in 3D Slicer
		fetch("/open-mask", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				snomed_code: snomedCode,
				file: fileName,
			}),
		})
			.then((response) => response.json())
			.then((data) => {
				if (data.success) {
					console.log("Successfully sent to 3D Slicer:", data.message);
				} else {
					console.error("Error opening 3D Slicer:", data.error);
				}
			})
			.catch((error) => {
				console.error("Network error:", error);
			});
	} else {
		console.error(`No file mapping found for SNOMED code: ${snomedCode}`);
		if (window.spineReportGenerator) {
			window.spineReportGenerator.showToast(
				`Unknown SNOMED code: ${snomedCode}`,
				"error"
			);
		}
	}
}

// Initialize the application when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
	window.spineReportGenerator = new SpineReportGenerator();
	console.log("MedSee.ai Spine Report Generator initialized");
});

// Add some additional CSS for clicked animation
const style = document.createElement("style");
style.textContent = `
    .clicked {
        transform: scale(1.1) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    
    .error-message {
        padding: 30px;
        text-align: center;
        color: #e53e3e;
        background-color: #fed7d7;
        border: 1px solid #feb2b2;
        border-radius: 8px;
        margin: 20px;
    }
    
    .error-message h3 {
        margin-bottom: 15px;
        color: #c53030;
    }
`;
document.head.appendChild(style);
