import os
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from llama_index.core import Document
#---------Libraries for image processing-------------
import torch
import clip
from PIL import Image
#--------Libraries for custom functionalites----------
from index_service.config import IndexConfig as settings
from index_service.utilities import TextProcessor as txtprocessor


class ImageProcessor:
    """Provide utilities to perform operations based upon image(s) retrieved from soruce data"""

    @classmethod
    def get_image_related_text(cls, label_texts: List[str], temp_dir: str, img_dir: str) -> Dict[str,str]:
        """Perform relevance search on given sequence of text and images and return a dictionary of text binded with most relevant image(s)"""
        print("[Image-text similarity] Performing image(s) relevance check for given text.....")

        #-------Configure CLIP Model--------
        model = settings.CLIP_MODEL
        preprocessor = settings.CLIP_PREPROCESSOR
        device = settings.DEVICE
        k = settings.CLIP_TOP_K
        
        text_inputs = clip.tokenize(label_texts).to(device)
        img_labels: Dict[str,str] = {}

        with torch.no_grad():
            text_features = model.encode_text(text_inputs)

        for img in os.listdir(temp_dir):
            image = preprocessor(Image.open(os.path.join(temp_dir,img))).unsqueeze(0).to(device)
            with torch.no_grad():
                image_features = model.encode_image(image)
                logits = image_features @ text_features.T
                probs = logits.softmax(dim=-1).squeeze(0)
            
            topk = probs.topk(k)
            top_indices = topk.indices.tolist()
            confidences = topk.values.tolist()
            labels = [label_texts[indx] for indx in top_indices]
            print(img, *[(label,confidence) for label,confidence in zip(labels,confidences)], sep='\n')
            print('\n')
            src = os.path.join(temp_dir,img)
            dst = os.path.join(img_dir,img)
            os.replace(src,dst)
            
            if not str(confidences[0]).split('.')[-1].startswith('00'):
                for label in labels:
                    img_labels[label] = img_labels.get(label,"") + f' {dst} '
        
        print("[Image-text similarity] Image(s) relevance check executed successfully.....")
        return img_labels
    

    @classmethod
    def get_image_captions_ocr(cls, image_docs: List[Document]) -> List[Document]:
        """Returns a Sequence of text documents baesed caption and OCR text for image(s) along with flag of successful completion task"""
        if not image_docs:
            return []
        
        print("[Image Processor] Running OCR and image captioning on new images in database.........")
        image_paths = [doc.metadata["image_path"] for doc in image_docs]

        with ThreadPoolExecutor(max_workers=2) as executor: 
            future_ocr = executor.submit(cls._run_ocr_batch, image_paths)
            future_caption = executor.submit(cls._run_caption_batch, image_paths)

            ocr_texts = future_ocr.result()
            captions = future_caption.result()
        
        final_docs: List[Document] = [
            Document(
                doc_id=doc.doc_id, 
                text=txtprocessor.normalize_content("\n".join([ocr, caption, doc.text])), 
                metadata=doc.metadata
            ) 
            for doc, ocr, caption in zip(image_docs, ocr_texts, captions)
        ]
        print(*[(doc.text,doc.metadata) for doc in final_docs], sep='\n\n')
        print("[Image Processor] OCR and image captioning on new images terminated successfully.........")
        return final_docs
    

    @classmethod
    def _run_caption_batch(cls, image_paths: List[str]) -> List[str]:
        """Return a Sequence of caption text for given images(s)"""
        #-----Configure image captioning model------
        model = settings.CAPTION_MODEL
        processor = settings.CAPTION_PROCESSOR
        device = settings.DEVICE
        
        captions: List[str] = []
        images = [Image.open(p).convert("RGB") for p in image_paths]
        try:
            inputs = processor(images=images, return_tensors="pt", padding=True).to(device)
            outputs = model.generate(**inputs)
            captions = [processor.decode(output, skip_special_tokens=True) for output in outputs]
        except Exception as e:
            print(f"[Image caption extractor] Captioning image batch failed: {e}")
            captions = ["" for _ in image_paths]
        return captions


    @ classmethod
    def _run_ocr_batch(cls, image_paths: List[str]) -> List[str]:
        """Returns a Sequence of OCR text for given image(s)"""
         #-----Configure ocr model------
        ocr_reader = settings.OCR_READER
        ocr_results: List[str] = []
        for path in image_paths:
            try:
                ocr = ocr_reader.readtext(path)
                ocr_text = "\n".join(text for (_, text, _) in ocr)
            except Exception as e:
                print(f"[Image OCR extractor] Image OCR failed for {path}: {e}")
                ocr_text = " "
            ocr_results.append(ocr_text)
        return ocr_results