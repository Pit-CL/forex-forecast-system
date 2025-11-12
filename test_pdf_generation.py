#!/usr/bin/env python3
"""
Simple test script to verify PDF generation works.

This creates a minimal PDF to test WeasyPrint installation.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Set library path for macOS
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get("DYLD_LIBRARY_PATH", "")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("PDF GENERATION TEST")
print("=" * 60)

try:
    from weasyprint import HTML
    print("\n✓ WeasyPrint imported successfully")
except Exception as e:
    print(f"\n✗ ERROR importing WeasyPrint: {e}")
    sys.exit(1)

# Create a simple HTML document
html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            color: #333;
        }
        h1 {
            color: #0066cc;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 10px;
        }
        .info {
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .success {
            color: #00aa00;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Forex Forecast System - Test de PDF</h1>

    <div class="info">
        <p><strong>Fecha:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <p><strong>Sistema:</strong> macOS con WeasyPrint</p>
        <p><strong>Propósito:</strong> Verificar generación de PDFs</p>
    </div>

    <h2>Prueba de Caracteres Españoles</h2>
    <p>
        Esta es una prueba de caracteres especiales del español:
    </p>
    <ul>
        <li>Vocales con tilde: á, é, í, ó, ú</li>
        <li>Letra ñ: año, señor, español</li>
        <li>Signos de exclamación: ¡Hola!</li>
        <li>Signos de interrogación: ¿Cómo estás?</li>
    </ul>

    <h2>Datos de Prueba</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr style="background-color: #0066cc; color: white;">
            <th style="padding: 10px; border: 1px solid #ddd;">Fecha</th>
            <th style="padding: 10px; border: 1px solid #ddd;">USD/CLP</th>
            <th style="padding: 10px; border: 1px solid #ddd;">Tendencia</th>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;">2025-11-12</td>
            <td style="padding: 10px; border: 1px solid #ddd;">950.50</td>
            <td style="padding: 10px; border: 1px solid #ddd;">Alcista</td>
        </tr>
        <tr style="background-color: #f9f9f9;">
            <td style="padding: 10px; border: 1px solid #ddd;">2025-11-13</td>
            <td style="padding: 10px; border: 1px solid #ddd;">952.30</td>
            <td style="padding: 10px; border: 1px solid #ddd;">Alcista</td>
        </tr>
    </table>

    <p class="success">
        ✓ Si puedes leer este PDF, la generación funciona correctamente.
    </p>
</body>
</html>
"""

# Create output directory
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

# Generate PDF
pdf_path = output_dir / f"test_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

print(f"\nGenerating PDF: {pdf_path}")

try:
    HTML(string=html_content).write_pdf(str(pdf_path))
    print(f"✓ PDF generated successfully!")
    print(f"  Location: {pdf_path.absolute()}")
    print(f"  Size: {pdf_path.stat().st_size:,} bytes")

    # Verify file exists and has content
    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        print("\n" + "=" * 60)
        print("SUCCESS: PDF generation is working!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Open the PDF to visually verify content")
        print("  2. Check Spanish characters render correctly")
        print("  3. Verify table formatting is correct")
        sys.exit(0)
    else:
        print("\n✗ PDF file is too small or doesn't exist")
        sys.exit(1)

except Exception as e:
    print(f"\n✗ ERROR generating PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
