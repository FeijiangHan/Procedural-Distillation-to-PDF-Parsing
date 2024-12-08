# LaTeX Web Viewer

A web-based tool for viewing and analyzing LaTeX documents. This application allows you to compile LaTeX files, view PDFs, and visualize document structure through automatic markup.

## Features

- LaTeX file viewing with syntax highlighting
- PDF compilation and viewing
- Automatic document structure markup
- Two-panel view (LaTeX source and marked PDF)
- COCO format annotations export

## Prerequisites

Before running the application, ensure you have the following installed:

- Python (v3.8 or later)
- LaTeX distribution (TeX Live recommended)
- Git

## Project Structure
```
tex2bbox/
├── data/
│   └── papers/
│       └── arXiv-2412.04472v1/
│           └── paper.tex
├── latex-web/
│   ├── backend/
│   │   ├── data/papers/  # Symlink to ../../data/papers
│   │   ├── output/       # Compilation outputs
│   │   ├── visualizations/  # Marked PDFs and annotations
│   │   ├── services/     # Service layer
│   │   │   ├── pipeline_service.py  # Main processing pipeline
│   │   │   ├── file_service.py      # File handling
│   │   │   └── ...
│   │   ├── process_aux/  # Auxiliary processing modules
│   │   ├── latex_marker/ # LaTeX marking modules
│   │   └── app.py        # Flask application
│   └── frontend/         # Vanilla JS frontend
│       ├── css/
│       ├── js/
│       └── index.html
└── run_pipeline.sh
```

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd tex2bbox
```

2. Create symbolic link for papers:
```bash
cd latex-web/backend
ln -s ../../data/papers data/papers
```

3. Install Python dependencies:
```bash
cd latex-web/backend
pip install -r requirements.txt
```

4. Start the backend server:
```bash
python app.py
```

5. Serve the frontend:
```bash
cd ../frontend
python -m http.server 3000
```

6. Access the application:
- Open your browser and navigate to `http://localhost:3000`
- The backend API will be available at `http://localhost:5000`

## Usage

1. Select a Paper:
   - Use the dropdown menu to select a paper (e.g., arXiv-2412.04472v1/paper.tex)
   - The LaTeX source will be displayed in the left panel

2. Process and View:
   - Click "Process" to compile and mark the document
   - The marked PDF will appear in the right panel
   - The process includes:
     - LaTeX compilation
     - Document structure analysis
     - Bounding box calculation
     - Visual markup generation

3. Export Annotations:
   - After processing, click "Export Annotations" to download
   - The export includes:
     - Marked PDF
     - Page images
     - COCO format annotations

## Output Structure

After processing, the following outputs are generated:

```
latex-web/backend/
├── output/
│   └── arXiv-2412.04472v1/
│       ├── paper.pdf           # Compiled PDF
│       ├── paper.aux          # Auxiliary files
│       └── ...
└── visualizations/
    └── arXiv-2412.04472v1/
        ├── paper_marked.pdf   # Marked PDF
        ├── pages/             # Individual page images
        │   ├── page_1.png
        │   └── ...
        └── annotations/       # COCO format annotations
            ├── page_1.json
            └── ...
```

## Development

### Backend API Endpoints

- `GET /api/papers` - List available papers
- `GET /api/tex/<paper_id>` - Get LaTeX content
- `POST /api/compile` - Process paper (compile and mark)
- `GET /api/marked-pdf/<paper_id>` - Get marked PDF
- `GET /api/export-annotations/<paper_id>` - Download annotations

### Frontend Components

- File selector
- LaTeX viewer with syntax highlighting
- PDF viewer with markup visualization
- Export functionality

## Troubleshooting

1. Backend Issues:
   - Check backend logs in `backend/logs/app.log`
   - Verify file permissions in output directories
   - Ensure LaTeX is properly installed

2. Frontend Issues:
   - Check browser console for errors
   - Clear browser cache if PDF viewer is blank
   - Verify API endpoint configuration

## License

This project is licensed under the MIT License - see the LICENSE file for details.