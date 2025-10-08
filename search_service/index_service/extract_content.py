import os
import uuid
import shutil
import mimetypes
from typing import List, Tuple
#--------------Libraries utilized in data extraction-------------
import cv2
import math
import numpy as np
from PIL import Image
from textdivider import split_text
from unstructured.partition.auto import partition
""" 
poppler, qpdf, tesseract, libreoffice, pandoc
are external dependencies to be installed locally on system as required by unstructured 
""" 
from llama_index.core import Document
#---------Libraries utilized for custom functionalities----------
from index_service.utilities import TextProcessor as txtprocessor


class DataExtractor:
    """Provides utilities to perform data extraction like operation on raw content from knowledge base"""

    @classmethod
    def extract(cls, filepath: str, img_dir: str, temp_img_dir: str, image_docs: List[Document]) -> Tuple[List[Document], List[str], str]:
        """Extract images, text from source data and returns following: (sequence of image documents, sequence of text in source data, storage directory of images extracted)"""

        print("[Data Extractor] Extracting Images from file :", filepath)
        filename = os.path.basename(filepath)
        file_text: List[str] = []

        mime_type, _ = mimetypes.guess_file_type(filepath)
        is_image_doc = mime_type and mime_type.startswith("image/")

        temp_dir = os.path.join(os.path.dirname(img_dir), f"{uuid.uuid4()}")
        os.makedirs(temp_dir, exist_ok=True)

        if is_image_doc:
            dst = os.path.join(img_dir, f"{filename}_{os.path.splitext(filepath)[1]}")
            try:
                shutil.copy(filepath, dst)
                image_docs.append(Document(
                    doc_id=dst,
                    text="", 
                    metadata={"file_name": filename, "file_path":dst, "image_path": dst}
                ))
                print("[Data Extractor] Image(s) extracted successfully to file :", dst)
            except Exception as e:
                print(f"[Data Extractor] Failed to move image {filepath}: {e}")
            return image_docs, [], temp_dir

        try:
            elements = partition(
                filepath, 
                extract_images_in_pdf=True, 
                extract_image_block=True, 
                extract_image_block_output_dir=temp_dir
            )
        except Exception as e:
            print(f"[Data Extractor][Warning] Could not parse data to extract images from {filename} :{e}")
            return image_docs, [], temp_dir

        for el in elements:
            if getattr(el, 'text', None):
                file_text.append(el.text.strip())

        for idx, src in enumerate(os.listdir(temp_dir)):
            src_path = os.path.join(temp_dir, src)
            ext = os.path.splitext(src)[1]
            discard_img = cls._is_useless_image(src_path)
            img_dst_dir = temp_img_dir
            img_name = f"{filename}_{idx}{ext}"
            if not discard_img:
                img_dst_loc = os.path.join(img_dir,img_name)
                image_docs.append(Document(
                    doc_id=img_dst_loc,
                    text="", 
                    metadata={"file_name": filename, "file_path":filepath, "image_path": img_dst_loc}
                ))
                img_dst_dir = temp_dir
            dst_path = os.path.join(img_dst_dir, img_name)
            try:
                os.replace(src_path, dst_path)
            except Exception as e:
                print(f"[Data Extractor] Failed to move image for file {filename} {src_path} :{e}")

        print("[Data Extractor] Image(s) extracted successfully from file :", filepath)
        text_chunks = cls._split_in_labels(text=file_text, chunk_size=77)
        return image_docs, text_chunks, temp_dir


    @classmethod
    def clean_temp_dir(cls, path: str, recreate: bool = False) -> None:
        """Clean an diectory at given path and recreate it if recreate is True"""
        if os.path.exists(path):
            shutil.rmtree(path)
        if recreate:
            os.makedirs(path, exist_ok=True)


    @classmethod
    def _split_in_labels(cls, *, text: List[str], chunk_size: int=77) -> List[str]:
        """Split text chunk of given sequence of text data in specific length chunk"""
        text = [txtprocessor.normalize_content(txt) for txt in text]
        text = [txt for txt in text if txt]
        chunks = []
        for sentence in text:
            chunk = split_text(sentence, chunk_size)
            chunks.extend(chunk)
        return chunks


    @classmethod
    def _is_useless_image(cls, image_path: str, min_size: tuple = (50, 50), entropy_thresh: float = 1.0, white_thresh: int = 245) -> bool:
        """Check whether an image is noise data generated in extraction process or not """
        print(f"[Image Validation Checker] Processing image {image_path} for validation......")

        try:
           # load image and convert to RGB (preserve original behavior)
            img = Image.open(image_path).convert("RGB")
            w, h = img.size

            # original size check: remove very small icons
            if w < min_size[0] or h < min_size[1]:
                return True

            # original entropy check: remove very-uniform images
            entropy = img.entropy()
            if entropy < entropy_thresh:
                return True

            img_np = np.asarray(img)
            total_pixels = h * w

            # original mostly-white check (kept, slightly tightened by default)
            white_pixels = np.sum(np.all(img_np > white_thresh, axis=2))
            white_ratio = white_pixels / total_pixels
            if white_ratio > 0.98:
                return True

            try:
                cv_img = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                qr_detector = cv2.QRCodeDetector()
                data, bbox, _ = qr_detector.detectAndDecode(cv_img)
                if bbox is not None and len(bbox) > 0:
                    return True
            except Exception:
                pass

            # 2) Edge density - preserve line diagrams even if low-color / mostly white
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            max_dim = 1024
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                gray_small = cv2.resize(gray, (math.ceil(w*scale), math.ceil(h*scale)))
            else:
                gray_small = gray
            edges = cv2.Canny(gray_small, 100, 200)
            edge_density = np.sum(edges > 0) / (gray_small.shape[0] * gray_small.shape[1])
            edge_density_thresh = 0.001
            low_edge = edge_density < edge_density_thresh

            # 3) Color diversity (approx): quantize & sample
            sample_w = min(300, w)
            sample_h = min(300, h)
            small = cv2.resize(img_np, (sample_w, sample_h))
            q_step = 32  # coarse quantization to detect color blocks
            quant = (small // q_step).astype(np.int32)
            unique_colors = np.unique(quant.reshape(-1, 3), axis=0).shape[0]
            low_color_diversity = unique_colors < 20

            # 4) Dominant horizontal band detection: conservative heuristic
            try:
                flattened = quant.reshape(-1, 3)
                vals, counts = np.unique(flattened.view([('', flattened.dtype)]*3), return_counts=True)
                dominant_idx = np.argmax(counts)
                dominant_color = flattened.reshape(-1,3)[dominant_idx]
                dominant_mask = ((img_np // q_step) == dominant_color).all(axis=2)
                coords = np.column_stack(np.where(dominant_mask))
                if coords.size > 0:
                    y0, x0 = coords.min(axis=0)
                    y1, x1 = coords.max(axis=0)
                    band_w = x1 - x0 + 1
                    band_h = y1 - y0 + 1
                    band_area = band_w * band_h
                    if (band_area / total_pixels) > 0.25 and (band_w / w) > 0.6 and (band_h / h) < 0.5:
                        return True
            except Exception:
                pass

            # 5) Left-icon + banner pattern: small square-ish icon on left + long low-variance area to right
            try:
                left_icon_frac = 0.18
                left_w = int(w * left_icon_frac)
                left_region = img_np[:, :left_w]
                left_nonwhite = np.sum(np.any(left_region < white_thresh, axis=2))
                left_nonwhite_frac = left_nonwhite / (h * left_w)
                if left_nonwhite_frac > 0.02 and low_color_diversity and low_edge:
                    right_region = img_np[:, left_w:]
                    right_quant = (right_region // q_step).reshape(-1,3)
                    right_unique = np.unique(right_quant, axis=0).shape[0]
                    if right_unique < 20:
                        return True
            except Exception:
                pass

            # Final conservative rule: low edge density AND low color diversity -> likely junk
            if low_edge and low_color_diversity:
                return True

            # original finishing print preserved
            print(f"[Image Validation Checker] Image {image_path} processed for validation successfully....")
            return False

        except Exception as e:
            print(f"[Image Validation Checker][Error] Cannot processing image {image_path} due to: {e}")
            return True