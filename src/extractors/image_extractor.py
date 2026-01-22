"""
Image and chart extraction from PDF using PyMuPDF.
"""
from typing import List, Dict, Any, Optional
import tempfile
import os
import io

import fitz  # PyMuPDF
from PIL import Image


class ImageExtractor:
    """Extract images and charts from PDF."""
    
    def __init__(self):
        self._temp_path: Optional[str] = None
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract all images from PDF bytes.
        
        Returns:
            List of dicts with 'image', 'page', 'bbox', 'type'
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            self._temp_path = tmp.name
        
        try:
            return self._extract_images(self._temp_path)
        finally:
            self._cleanup()
    
    def _extract_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract images using PyMuPDF."""
        images = []
        
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_idx, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    if base_image:
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Convert to PIL Image
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Get image info
                        width, height = pil_image.size
                        
                        # Classify image type
                        img_type = self._classify_image(pil_image, width, height)
                        
                        images.append({
                            "image": pil_image,
                            "bytes": image_bytes,
                            "page": page_num + 1,
                            "index": img_idx,
                            "width": width,
                            "height": height,
                            "format": image_ext,
                            "type": img_type,
                            "xref": xref
                        })
                except Exception as e:
                    continue
        
        doc.close()
        return images
    
    def _classify_image(self, image: Image.Image, width: int, height: int) -> str:
        """Classify image type (chart, logo, photo, etc.)."""
        aspect_ratio = width / height if height > 0 else 1
        
        # Very small images are likely icons/logos
        if width < 150 and height < 150:
            return "icon"
        
        # Small square-ish images are likely logos or decorative icons
        if width < 300 and height < 300 and 0.7 < aspect_ratio < 1.4:
            return "logo"
        
        # Images that are too small to be meaningful charts
        if width < 250 or height < 150:
            return "icon"
        
        # Wide images with typical chart dimensions (line charts, bar charts)
        if width > 350 and height > 200 and 1.2 < aspect_ratio < 3.5:
            return "chart"
        
        # Tall images might be vertical bar charts
        if height > 350 and width > 200 and 0.3 < aspect_ratio < 0.9:
            return "chart"
        
        # Large square-ish images could be pie charts or data visualizations
        if width > 300 and height > 300:
            return "chart_or_figure"
        
        # Medium sized images - be conservative, might be decorative
        if width > 250 and height > 200:
            return "chart_or_figure"
        
        return "unknown"
    
    def extract_charts_only(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract only images classified as charts, with additional filtering."""
        all_images = self.extract_from_bytes(pdf_bytes)
        
        charts = []
        for img in all_images:
            # Must be classified as chart type
            if img["type"] not in ["chart", "chart_or_figure"]:
                continue
            
            # Additional size filter - real charts are usually substantial
            if img["width"] < 300 or img["height"] < 180:
                continue
            
            # Skip very small file sizes (likely simple graphics)
            if len(img.get("bytes", b"")) < 5000:
                continue
            
            # Check if image has enough color variation (not just icons)
            try:
                pil_img = img["image"]
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                
                # Get color statistics
                colors = pil_img.getcolors(maxcolors=1000)
                if colors and len(colors) < 20:
                    # Too few colors - likely a simple icon or logo
                    continue
            except:
                pass
            
            charts.append(img)
        
        return charts
    
    def render_page_as_image(
        self, 
        pdf_bytes: bytes, 
        page_num: int, 
        dpi: int = 150
    ) -> Optional[Image.Image]:
        """Render a specific PDF page as an image."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            doc = fitz.open(tmp_path)
            
            if page_num < 1 or page_num > len(doc):
                return None
            
            page = doc[page_num - 1]
            
            # Render at specified DPI
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            doc.close()
            return img
        
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def get_image_for_vision(
        self, 
        image_data: Dict[str, Any], 
        max_size: int = 1024
    ) -> bytes:
        """
        Prepare image for vision model (resize if needed, convert to bytes).
        """
        image = image_data["image"]
        
        # Resize if too large
        width, height = image.size
        if width > max_size or height > max_size:
            ratio = min(max_size / width, max_size / height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    
    def _cleanup(self):
        """Clean up temporary files."""
        if self._temp_path and os.path.exists(self._temp_path):
            try:
                os.unlink(self._temp_path)
            except:
                pass
            self._temp_path = None
