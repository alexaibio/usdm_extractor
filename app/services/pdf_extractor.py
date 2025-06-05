import io
import json
import string
from pathlib import Path
from injector import inject
import os
import re
from typing import Optional, Tuple
import requests
from PIL import Image
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from app.core.settings import Settings



class GrobidClient:
    def __init__(self, url: str):
        self._base_url = url

    def check_server(self) -> bool:
        try:
            response = requests.get(f"{self._base_url}/api/isalive", timeout=5)
            response.raise_for_status()
            print(f"GROBID server at {self._base_url} is alive.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"GROBID server at {self._base_url} is not reachable: {e}")
            return False

    def call_process_fulltext(self, pdf_path: str) -> str:
        grobid_api_url = f"{self._base_url}/api/processFulltextDocument"
        try:
            coord_tags = {'figure', 'table', 'formula', 'list', 'item',
                          'label'}  # {'list', 'item', 'figure', 'formula', 'table'}
            params = {
                'consolidateHeader': '1',
                'consolidateCitations': '1',
                'includeRawCitations': '0',
                'includeRawAffiliations': '0',
                'teiCoordinates': list(coord_tags)  # Запрашиваем координаты!
            }
            with open(pdf_path, 'rb') as f:
                files = {'input': f}
                response = requests.post(grobid_api_url, files=files, data=params, timeout=240)  # Увеличим таймаут

            response.raise_for_status()
            print(f"Successfully processed PDF with GROBID: {pdf_path}")
            return response.text
        except requests.exceptions.Timeout:
            print(f"GROBID request timed out for {pdf_path}.")
            return ""
        except requests.exceptions.ConnectionError as e:
            print(f"Could not connect to GROBID server at {self._base_url}. Is it running? Error: {e}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"Error calling GROBID API for {pdf_path}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"GROBID Response Status Code: {e.response.status_code}")
                print(f"GROBID Response Text: {e.response.text[:500]}...")  # Показать начало ответа
            return ""
        except Exception as e:
            print(f"An unexpected error occurred during GROBID processing for {pdf_path}: {e}")
            return ""



class PDFConvertor:
    @inject
    def __init__(self, client: GrobidClient, settings: Settings):
        self._client = client


    def _add_period_to_sentence(self, sentence:Optional[str]):
        if sentence and sentence[-1] not in string.punctuation:
            sentence += '.'
        return sentence

    def _extract_page_and_bbox(self, coords: str, offset: float = 0.0):
        parts = coords.split(',')
        if len(parts) == 5:
            page = int(parts[0]) - 1
            x, y, w, h = map(float, parts[1:])
            bbox = (x-2, y-2, x + w + offset + 2, y + h + 2)

            return page, bbox

        return None, None

    def _extract_media_blocks(self, soup):
        results = {}
        for ref_tag in soup.find_all("ref") or []:
            type_element = ref_tag.get("type") or ""
            if type_element in ["figure", "table"]:
                target = (ref_tag.get("target") or "").replace('#', '')
                if target:
                    figure_tag = soup.find("figure", {"xml:id": target})
                    if figure_tag:
                        if type_element == "figure":
                            graphics = figure_tag.find("graphic")
                            if graphics:
                                page_num, bbox = self._extract_page_and_bbox(graphics.get("coords") or "")
                                if page_num is not None:
                                    key = f"{type_element}_{page_num + 1}_{target}"
                                    results[key] = {"page": page_num, "bbox": bbox}
                                    ref_tag.replace_with(f" _IMAGE_[{key}]_ ")

                        elif type_element == "table":
                            table = figure_tag.find("table")
                            coords = table.get("coords") if table else figure_tag.get("coords")

                            page_num, bbox = self._extract_page_and_bbox(coords or figure_tag.get("coords"))
                            if page_num is not None:
                                key = f"{type_element}_{page_num + 1}_{target}"
                                results[key] = {"page": page_num, "bbox": bbox}
                                ref_tag.replace_with(f" _IMAGE_[{key}]_ ")

        return results


    def _extract_formulas_blocks(self, soup):
        results = {}
        for formula_tag in soup.find_all("formula") or []:
            element_id = formula_tag.get("xml:id")
            text = formula_tag.get_text() or ""
            if len(text) <= 1:
                formula_tag.replace_with(f"{text} ")
                continue

            if element_id is not None:
                page_num, bbox = self._extract_page_and_bbox(formula_tag.get("coords") or "", 2.0)
                if page_num is not None:
                    key = f"formula_{page_num + 1}_{element_id}"
                    results[key] = {"page": page_num, "bbox": bbox}
                    formula_tag.replace_with(f" _FORMULA_[{key}]_ ")
        return results

    def _extract_content(self, soup):
        def extract_title(header):
            title_tag = header.find("title") if header else None
            return self._add_period_to_sentence( title_tag.get_text() ) if title_tag else ""

        title = extract_title(soup.find("teiHeader"))
        body_tag = soup.find("body") or soup.find("text")
        divs = body_tag.find_all("div") or [] if body_tag else []
        text = "\n".join([tag.get_text() for tag in divs]) or ""

        return f"{title}\n{text}"


    def _replace_all_head(self, soup):
        for head_tag in soup.find_all("head"):
            number = head_tag.get("n")
            text = head_tag.get_text() or ""
            if number is not None:
                text = f"\n{number} {self._add_period_to_sentence( text )}\n"
            else:
                text = f"\n{self._add_period_to_sentence( text )}\n"
            head_tag.replace_with(text)


    def _clean_text(self, text: str, remove_extra_whitespace: bool = True) -> str:
        # Remove all NBSP
        cleared_text = re.sub(r'\xa0', ' ', text)
        if remove_extra_whitespace:
            # Удаляем пробелы перед знаками препинания в начале строки
            cleared_text = re.sub(r'\s+([.,!?;:])', r'\1', cleared_text)
            #cleared_text = re.sub(r'([.,!?;:])(\S)', r'\1 \2', cleared_text)

            cleared_text = re.sub('\t+', ' ', cleared_text)
            # cleared_text = re.sub('\n+', '\n', cleared_text)
            cleared_text = re.sub('\n+', ' ', cleared_text)
            cleared_text = re.sub(' +', ' ', cleared_text)

        return cleared_text.strip()


    def extract_text_from_pdf(self, pdf_path: str, output_dir: str):
        filename = Path(pdf_path).stem

        print("Processing PDF with GROBID...")
        tei_xml = self._client.call_process_fulltext(pdf_path)
        if not tei_xml:
            print("Failed to get TEI XML from GROBID. Aborting.")
            raise Exception("Failed to get TEI XML from GROBID. Aborting.")

        print("Successfully received TEI XML from GROBID.")
        #os.makedirs("./data/output_dir", exist_ok=True)
        with open(os.path.join("./data/output_dir", f"{filename}.xml"), "w", encoding="utf-8") as f_xml:
             f_xml.write(tei_xml)

        soup = BeautifulSoup(tei_xml, 'lxml-xml')

        self._replace_all_head(soup)


        doc = None
        try:
            doc = fitz.open(pdf_path)
            print(f"PDF opened successfully with PyMuPDF: {len(doc)} pages.")

            for element_id, info in media_results.items():
                page_num, bbox = info["page"], info["bbox"]
                info["filepath"] = self._extract_element_image(doc, page_num, bbox, element_id, media_path)

            for element_id, info in formula_results.items():
                page_num, bbox = info["page"], info["bbox"]
                info["filepath"] = self._extract_element_image(doc, page_num, bbox, element_id, media_path)

            # for element_id, info in formula_results.items():
            #     info["formula"] = self._formula_convertor.convert(info["filepath"])

            full_text = self._extract_content(soup)

            for element_id, info in formula_results.items():
                #formula = info["formula"]
                #full_text = full_text.replace(f'_FORMULA_[{element_id}]_', f'_LATEX_FORMULA_[{formula}]_ ', -1)
                content_url = f"{media_url}/{source}/{filename}/{element_id}.png"
                full_text = full_text.replace(f'_FORMULA_[{element_id}]_', f'_IMAGE_[{content_url}]_ ', -1)

            for element_id, info in media_results.items():
                content_url = f"{media_url}/{source}/{filename}/{element_id}.png"
                full_text = full_text.replace(f'_IMAGE_[{element_id}]_', f'_IMAGE_[{content_url}]_ ', -1)

            full_text = self._clean_text(full_text)

            with open(os.path.join(media_path, f"{filename}.json"), "w", encoding="utf-8") as f_json:
                json.dump(formula_results, f_json)

            return full_text

        except Exception as e:
            print(f"Failed to open PDF {pdf_path} with PyMuPDF: {e}")
            raise e
        finally:
            if doc is not None:
                doc.close()


    def _extract_element_image(self, doc: fitz.Document, page_num: int, bbox: Tuple[float, float, float, float], element_id: str, media_dir: str) -> str:
        try:
            is_formula = element_id.startswith("formula")

            page = doc.load_page(page_num)
            # Увеличиваем разрешение для лучшего OCR / отображения
            zoom = 4 if is_formula else 2

            mat = fitz.Matrix(zoom, zoom)
            # Обрезаем страницу по bbox
            # PyMuPDF rect: [x0, y0, x1, y1]
            rect = fitz.Rect(bbox)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            img_path = os.path.join(media_dir, f"{element_id}.png")
            if element_id.startswith("formula"):
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img = preprocess_image(img)
                img.save(img_path)
            else:
                pix.save(img_path)
            print(f"Saved element image: {img_path}")
            return img_path
        except Exception as e:
            print(f"Error extracting element image on page {page_num + 1} for bbox {bbox}: {e}")
            return ""
