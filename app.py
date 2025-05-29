# app.py (unchanged from previous version)
import os
import fitz  # PyMuPDF
import zipfile
import io
import base64
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_images():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({"error": "Empty filename."}), 400
    
    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Please upload a PDF file."}), 400

    try:
        pdf_data = file.read()
        doc = fitz.open(stream=pdf_data, filetype="pdf")

        images = []
        for page_number in range(len(doc)):
            for img_index, img in enumerate(doc.get_page_images(page_number)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                filename = f"page{page_number + 1}_img{img_index + 1}.{ext}"
                base64_img = base64.b64encode(image_bytes).decode('utf-8')
                images.append({
                    "filename": filename,
                    "ext": ext,
                    "base64": base64_img,
                    "size": f"{(len(image_bytes) / 1024):.1f} KB",
                    "dimensions": f"{base_image['width']}×{base_image['height']}px"
                })

        doc.close()

        if not images:
            return jsonify({"error": "No embedded images found in the PDF."}), 404

        return jsonify({
            "images": images,
            "summary": {
                "total_images": len(images),
                "original_filename": secure_filename(file.filename)
            }
        })

    except Exception as e:
        return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500

@app.route('/download-zip', methods=['POST'])
def download_zip():
    image_data = request.json.get('images')
    if not image_data:
        return jsonify({"error": "No images to zip"}), 400

    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img in image_data:
                filename = img['filename']
                image_bytes = base64.b64decode(img['base64'])
                zipf.writestr(filename, image_bytes)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='pdf-images.zip'
        )
    except Exception as e:
        return jsonify({"error": f"Error creating zip file: {str(e)}"}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
