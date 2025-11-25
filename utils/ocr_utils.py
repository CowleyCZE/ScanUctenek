"""
OCR utility for receipt processing
Handles image preprocessing and OCR operations
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import re
import tempfile
import requests
import logging
from typing import Tuple, Dict, List, Optional, Any, Union
from functools import lru_cache

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OCR configuration
OCR_CONFIG = {
    'language': 'ces',
    'psm': 6,
    'oem': 3,
    'confidence_threshold': 40,
    'whitelist': None,
    'scale': 1,
    'deskew': True,
    'profile': os.environ.get('OCR_PROFILE', 'default')
}

@lru_cache(maxsize=128)
def compile_pattern(pattern: str) -> re.Pattern:
    """
    Kompiluje a cachuje regulární výraz.
    
    Args:
        pattern: Vzorek regulárního výrazu
        
    Returns:
        Kompilovaný regulární výraz
    """
    return re.compile(pattern)

def _deskew(gray: np.ndarray) -> np.ndarray:
    try:
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bw = cv2.bitwise_not(bw)
        coords = np.column_stack(np.where(bw > 0))
        if coords.size == 0:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return gray

def preprocess_image(image: Union[np.ndarray, Image.Image]) -> np.ndarray:
    """
    Předzpracuje obrázek pro lepší výsledky OCR.
    
    Args:
        image: Vstupní obrázek (numpy array nebo PIL Image)
        
    Returns:
        Předzpracovaný obrázek (numpy array)
    """
    try:
        # Převod na numpy array pokud je potřeba
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        # Kontrola typu vstupu
        if not isinstance(image, np.ndarray):
            logger.error("Vstupní obrázek není numpy array")
            return image
            
        # Převod na uint8 pokud není
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)
            
        # Převod na stupně šedi pokud není
        if len(image.shape) == 3:
            if image.shape[2] == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
            elif image.shape[2] == 3:  # RGB nebo BGR
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            image = image.copy()
            
        # Kontrola, že obrázek je ve stupních šedi
        if len(image.shape) != 2:
            logger.error("Nepodařilo se převést obrázek na stupně šedi")
            return image
            
        # Upscale
        try:
            scale = float(os.environ.get('OCR_SCALE', OCR_CONFIG['scale']))
            if scale and scale > 1.0:
                interp = cv2.INTER_LINEAR if OCR_CONFIG.get('profile') in ['dotmatrix', 'thermal'] else cv2.INTER_CUBIC
                image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=interp)
                logger.info(f"Preprocess: scale={scale}")
        except Exception:
            pass

        # Redukce šumu
        try:
            if OCR_CONFIG.get('profile') in ['dotmatrix', 'thermal']:
                image = cv2.medianBlur(image, 3)
            else:
                image = cv2.fastNlMeansDenoising(image, None, 7, 7, 21)
        except Exception:
            image = cv2.medianBlur(image, 3)

        # Vylepšení kontrastu pomocí CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)

        # Deskew volitelně
        try:
            deskew_env = os.environ.get('OCR_DESKEW')
            deskew = OCR_CONFIG['deskew'] if deskew_env is None else deskew_env.lower() in ['1', 'true', 'yes']
            if deskew:
                enhanced = _deskew(enhanced)
                logger.info("Preprocess: deskew applied")
        except Exception:
            pass

        # Thresholding + morfologie
        if OCR_CONFIG.get('profile') in ['dotmatrix', 'thermal']:
            adp = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 7)
            result = adp
        else:
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((2, 2), np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            blurred = cv2.GaussianBlur(closed, (0, 0), 1.0)
            result = cv2.addWeighted(closed, 1.5, blurred, -0.5, 0)

        return result
    except Exception as e:
        logger.error(f"Chyba při předzpracování obrázku: {str(e)}")
        return image

def preprocess_variants(image: Union[np.ndarray, Image.Image]) -> List[np.ndarray]:
    try:
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        variants: List[np.ndarray] = []

        # Variant A: current pipeline (scale/env driven)
        vA = preprocess_image(img)
        variants.append(vA)
        logger.debug("Variant A ready")

        # Variant B: bilateral + CLAHE + adaptive threshold (more tolerant to low contrast)
        b = cv2.bilateralFilter(img, 9, 75, 75)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        b = clahe.apply(b)
        adp = cv2.adaptiveThreshold(b, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)
        variants.append(adp)
        logger.debug("Variant B ready")

        # Variant C: CLAHE + Otsu + mild close
        c = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
        _, c = cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        c = cv2.morphologyEx(c, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
        variants.append(c)
        logger.debug("Variant C ready")

        # Variant D: no threshold, just CLAHE
        d = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
        variants.append(d)
        logger.debug("Variant D ready")

        # Variant E: inverted after Otsu
        e = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
        _, e = cv2.threshold(e, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        e = cv2.bitwise_not(e)
        variants.append(e)

        # Variant F: Sauvola local thresholding
        try:
            w = 31
            k = 0.2
            R = 128
            pad = w // 2
            src = img.astype(np.float32)
            src_p = cv2.copyMakeBorder(src, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            ones = np.ones_like(src_p, dtype=np.float32)
            m = cv2.boxFilter(src_p, ddepth=-1, ksize=(w, w))
            m2 = cv2.boxFilter(src_p*src_p, ddepth=-1, ksize=(w, w))
            var = m2 - m*m
            std = cv2.sqrt(cv2.max(var, 0))
            T = m * (1 + k * ((std / R) - 1))
            T_cropped = T[pad:-pad, pad:-pad]
            f = (src > T_cropped).astype(np.uint8) * 255
            variants.append(f)
            logger.debug("Variant F ready")
        except Exception:
            pass

        # Variant G: dot-matrix friendly (no NLM, adaptive threshold, no close)
        try:
            g = cv2.medianBlur(img, 3)
            g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
            g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
            variants.append(g)
            logger.debug("Variant G ready")
        except Exception:
            pass
        logger.debug("Variant E ready")
        
        return variants
    except Exception:
        return [preprocess_image(image)]

def perform_ocr(image: Union[np.ndarray, Image.Image], language: str = 'ces', ocr_provider: str = 'tesseract') -> Tuple[str, Dict[str, Any]]:
    """
    Provede OCR na zadaném obrázku pomocí Tesseractu.
    
    Args:
        image: Vstupní obrázek (numpy array nebo PIL Image)
        language: Jazyk pro OCR
        ocr_provider: OCR engine (pouze tesseract je podporován)
        
    Returns:
        Tuple obsahující (extrahovaný_text, strukturovaná_data)
    """
    try:
        if image is None:
            raise ValueError("Vstupní obrázek je prázdný")
            
        # Nastavení cesty k Tesseractu
        try:
            tcmd = os.environ.get('TESSERACT_CMD')
            if tcmd:
                pytesseract.pytesseract.tesseract_cmd = tcmd
            else:
                candidates = [
                    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                    r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                ]
                for c in candidates:
                    if os.path.exists(c):
                        pytesseract.pytesseract.tesseract_cmd = c
                        break
        except Exception:
            pass

        # Převod na PIL Image pokud je potřeba
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        elif not isinstance(image, Image.Image):
            raise ValueError("Nepodporovaný formát obrázku")
            
        # Kontrola, zda je obrázek validní
        if image.size[0] == 0 or image.size[1] == 0:
            raise ValueError("Neplatný obrázek - nulová velikost")
            
        # Předzpracování obrázku
        processed_image = preprocess_image(image)
        if processed_image is None:
            raise ValueError("Předzpracování obrázku selhalo")
            
        # Převod zpět na PIL Image pro OCR
        pil_image = Image.fromarray(processed_image)
        
        # Konfigurace (s možností override přes env)
        level = os.environ.get('LOG_LEVEL', 'INFO')
        try:
            logger.setLevel(getattr(logging, level))
        except Exception:
            pass
        oem = int(os.environ.get('OCR_OEM', OCR_CONFIG['oem']))
        psm = int(os.environ.get('OCR_PSM', OCR_CONFIG['psm']))
        whitelist = os.environ.get('OCR_WHITELIST', '')
        if not whitelist and OCR_CONFIG.get('profile') in ['dotmatrix', 'thermal']:
            whitelist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÂÄÇÈÉÊËÎÏÔÛÙÜàâäçèéêëîïôûùü0123456789€:/\\.,-+% '
        conf_thr = int(os.environ.get('OCR_CONF_THRESH', OCR_CONFIG['confidence_threshold']))

        custom_config = (
            f'--oem {oem} '
            f'--psm {psm} '
            f'-l {language} '
            f'-c preserve_interword_spaces=1 '
            f'-c user_defined_dpi=400 '
            f'-c textord_heavy_nr=1 '
        )
        if whitelist:
            custom_config += f'-c tessedit_char_whitelist={whitelist}'
        logger.info(f"OCR: lang={language}, psm={psm}, oem={oem}, whitelist={'on' if whitelist else 'off'}")
        
        # Získání textu z obrázku s lepším ošetřením chyb
        try:
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            if not text.strip():
                logger.warning("OCR nedetekoval žádný text")
                
            # Získání strukturovaných dat
            data = pytesseract.image_to_data(
                pil_image,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Filtrování dat s nízkou důvěryhodností
            confidence_threshold = conf_thr
            filtered_data = {
                key: [val for i, val in enumerate(data[key]) 
                      if float(data['conf'][i]) > confidence_threshold]
                for key in data.keys()
            }
            
            # Vytvoření strukturovaných dat
            # Vytvoření strukturovaných dat
            confidence_values = [float(conf) for conf in data['conf'] if float(conf) > 0]
            mean_confidence = np.mean(confidence_values) if confidence_values else 0.0
            logger.info(f"OCR: mean_confidence={mean_confidence:.2f}, conf_thr={confidence_threshold}")

            structured_data = {
                'merchant': '',
                'date': None,
                'total': 0.0,
                'items': [],
                'metadata': {
                    'language': language,
                    'confidence': mean_confidence,
                    'processing_time': None
                }
            }
            
            # Pokus o nalezení částky v textu
            amount_matches = re.findall(r'(?:TOTAAL|TOTAL|SUMA|CELKEM)[\s:]*[€]?\s*(\d+[.,]\d{2})', text, re.IGNORECASE)
            if amount_matches:
                try:
                    structured_data['total'] = float(amount_matches[-1].replace(',', '.'))
                except ValueError:
                    pass
            
            # Multipass: pokud je málo písmen, zkus jiný jazyk/PSM
            try:
                alpha_ratio = (sum(c.isalpha() for c in text) / max(1, len(text)))
                multipass = os.environ.get('OCR_MULTIPASS', '0') in ['1', 'true', 'yes']
                if multipass and alpha_ratio < 0.15:
                    logger.info(f"OCR: low alpha_ratio={alpha_ratio:.3f}, trying multipass")
                    candidates_lang = []
                    override = os.environ.get('OCR_LANG_OVERRIDE', 'auto')
                    if override in ['cs', 'fr', 'de']:
                        map_lang = {'cs': 'ces', 'fr': 'fra', 'de': 'deu'}
                        candidates_lang = [map_lang[override]]
                    else:
                        candidates_lang = [language, 'fra', 'deu']
                    candidates_psm = [psm, 4, 6]
                    best_text = text
                    best_ratio = alpha_ratio
                    for lang_try in candidates_lang:
                        for psm_try in candidates_psm:
                            cfg = f'--oem {oem} --psm {psm_try} -l {lang_try} -c preserve_interword_spaces=1'
                            alt_text = pytesseract.image_to_string(pil_image, config=cfg)
                            r = (sum(c.isalpha() for c in alt_text) / max(1, len(alt_text)))
                            logger.debug(f"OCR try: lang={lang_try}, psm={psm_try}, alpha_ratio={r:.3f}")
                            if r > best_ratio:
                                best_ratio = r
                                best_text = alt_text
                    logger.info(f"OCR multipass selected alpha_ratio={best_ratio:.3f}")
                    text = best_text
            except Exception:
                pass

            return text.strip(), structured_data
            
        except pytesseract.TesseractError as te:
            logger.error(f"Tesseract chyba: {str(te)}")
            return "", {}
        except pytesseract.pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract není nainstalován nebo není v PATH")
            return "", {}
            
    except Exception as e:
        logger.error(f"OCR chyba: {str(e)}")
        return "", {}

def extract_text_blocks(image: np.ndarray, language: str = 'ces') -> List[Dict[str, Any]]:
    """
    Extrahuje textové bloky s informacemi o pozicích.
    
    Args:
        image: Vstupní obrázek (numpy array)
        language: Jazyk pro OCR
        
    Returns:
        Seznam slovníků s textem a informacemi o pozicích
    """
    # Mapování jazykových kódů
    lang_map = {
        'ces': 'ces',
        'fra': 'fra',
        'deu': 'deu',
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    }
    
    # Získání správného jazykového kódu
    lang_code = lang_map.get(language, 'ces')
    
    try:
        # Předzpracování obrázku
        processed_image = preprocess_image(image)
        
        # Převod NumPy array na PIL Image
        pil_image = Image.fromarray(processed_image)
        
        # Extrakce textu s daty o pozicích
        custom_config = f'--oem {OCR_CONFIG["oem"]} --psm {OCR_CONFIG["psm"]} -l {lang_code}'
        data = pytesseract.image_to_data(pil_image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        blocks = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > OCR_CONFIG['confidence_threshold'] and data['text'][i].strip():
                block = {
                    'text': data['text'][i].strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': data['conf'][i]
                }
                
                blocks.append(block)
                
        return blocks
        
    except Exception as e:
        logger.error(f"Chyba při extrakci textových bloků: {str(e)}")
        
        # Fallback na metodu založenou na souborech
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_filename = tmp.name
            try:
                cv2.imwrite(tmp_filename, processed_image)
                
                # Extrakce textu s daty o pozicích
                custom_config = f'--oem {OCR_CONFIG["oem"]} --psm {OCR_CONFIG["psm"]} -l {lang_code}'
                data = pytesseract.image_to_data(Image.open(tmp_filename), config=custom_config, output_type=pytesseract.Output.DICT)
                
                blocks = []
                for i in range(len(data['text'])):
                    if int(data['conf'][i]) > OCR_CONFIG['confidence_threshold'] and data['text'][i].strip():
                        block = {
                            'text': data['text'][i].strip(),
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': data['conf'][i]
                        }
                        
                        blocks.append(block)
                        
                return blocks
                
            finally:
                if os.path.exists(tmp_filename):
                    os.unlink(tmp_filename)
                    
        return []

def _evaluate_text_quality(text: str, language: str) -> float:
    try:
        total = max(1, len(text))
        alpha = sum(1 for c in text if c.isalpha()) / total
        digits = sum(1 for c in text if c.isdigit()) / total
        words = re.findall(r'[A-Za-zÀ-ÿ]+', text)
        avg_len = (sum(len(w) for w in words) / max(1, len(words))) if words else 0.0
        vowels_map = {
            'ces': set(list('aeiouyáéíóúůýěřčšďťň')),
            'fra': set(list('aeiouyàâçèéêëîïôûùü')),
            'deu': set(list('aeiouyäöüß'))
        }
        vowels = vowels_map.get(language, set(list('aeiouy')))
        vowel_ratio = sum(1 for c in text.lower() if c in vowels) / total
        lex_boost = 0.0
        if language == 'fra':
            keywords = ['avia', 'montant', 'reel', 'réel', 'debit', 'carburant', 'gazole', 'quantite', 'quantité', 'tva', 'euro']
            t = text.lower()
            hits = sum(1 for k in keywords if k in t)
            lex_boost = min(0.3, hits * 0.03)
        quality = alpha*0.6 + vowel_ratio*0.2 + (avg_len/10.0)*0.2 - digits*0.2 + lex_boost
        return quality
    except Exception:
        return 0.0

def auto_ocr_optimize(image: Union[np.ndarray, Image.Image], initial_lang: str, max_iters: int = 6, threshold: float = 0.25) -> Tuple[str, Dict[str, Any]]:
    try:
        if isinstance(image, Image.Image):
            image_np = np.array(image)
        else:
            image_np = image
        processed_list = preprocess_variants(image_np)
        langs = [initial_lang]
        if initial_lang != 'fra':
            langs.append('fra')
        if initial_lang != 'deu':
            langs.append('deu')
        psms = [int(os.environ.get('OCR_PSM', OCR_CONFIG['psm'])), 4, 6, 11, 12, 7]
        scales = [float(os.environ.get('OCR_SCALE', 1.0)), 1.5, 2.0, 2.5, 3.0]
        oems = [int(os.environ.get('OCR_OEM', OCR_CONFIG['oem'])), 1, 3]
        tried = set()
        best_text = ""
        best_params = {'lang': initial_lang, 'psm': psms[0], 'scale': scales[0], 'deskew': os.environ.get('OCR_DESKEW', '1'), 'variant': 0}
        best_score = -1.0
        iters = 0
        for v_idx, processed in enumerate(processed_list):
            for lang in langs:
                for psm in psms:
                    for scale in scales:
                        for oem in oems:
                            key = f"{lang}-{psm}-{scale}"
                            if key in tried:
                                continue
                            tried.add(key)
                            iters += 1
                            if iters > max_iters:
                                break
                        os.environ['OCR_PSM'] = str(psm)
                        os.environ['OCR_SCALE'] = str(scale)
                        os.environ['OCR_OEM'] = str(oem)
                        text, _ = perform_ocr(processed, lang)
                        score = _evaluate_text_quality(text, lang)
                        logger.debug(f"AutoOCR: variant={v_idx}, lang={lang}, psm={psm}, scale={scale}, score={score:.3f}")
                        if score > best_score:
                            best_score = score
                            best_text = text
                            best_params = {'lang': lang, 'psm': psm, 'scale': scale, 'oem': oem, 'deskew': os.environ.get('OCR_DESKEW', '1'), 'variant': v_idx}
                        if score >= threshold:
                            logger.info(f"AutoOCR selected: variant={v_idx}, lang={lang}, psm={psm}, oem={oem}, scale={scale}, score={score:.3f}")
                            os.environ['OCR_PSM'] = str(psm)
                            os.environ['OCR_SCALE'] = str(scale)
                            os.environ['OCR_OEM'] = str(oem)
                            return best_text, best_params
        logger.info(f"AutoOCR best: variant={best_params['variant']}, lang={best_params['lang']}, psm={best_params['psm']}, oem={best_params.get('oem')}, scale={best_params['scale']}, score={best_score:.3f}")
        os.environ['OCR_PSM'] = str(best_params['psm'])
        os.environ['OCR_SCALE'] = str(best_params['scale'])
        if 'oem' in best_params:
            os.environ['OCR_OEM'] = str(best_params['oem'])
        return best_text, best_params
    except Exception:
        return "", {'lang': initial_lang, 'psm': OCR_CONFIG['psm'], 'scale': 1.0, 'deskew': os.environ.get('OCR_DESKEW', '1')}
