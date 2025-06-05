import httpx


class GrobidClient:
    def __init__(self, base_url: str):
        self._client = httpx.Client(base_url=base_url, timeout=240)

    def check_server(self) -> bool:
        try:
            response = self._client.get("/api/isalive", timeout=5)
            response.raise_for_status()

            print(f"GROBID server at {self._client.base_url} is alive.")
            return True
        except Exception as e:
            print(f"GROBID server at {self._client.base_url} is not reachable: {e}")
            return False

    def call_process_fulltext(self, pdf_path: str) -> str:
        try:
            #coord_tags = {'figure', 'table', 'formula', 'list', 'item', 'label'}
            coord_tags = { 'table'}
            params = {
                'consolidateHeader': '1',
                'consolidateCitations': '1',
                'includeRawCitations': '0',
                'includeRawAffiliations': '0',
                'teiCoordinates': list(coord_tags)
            }
            with open(pdf_path, 'rb') as f:
                files = {'input': f}
                data = {'teiCoordinates': True, 'segmentSentences': True}
                response = self._client.post("/api/processFulltextDocument", files=files, data=data)

            response.raise_for_status()
            print(f"Successfully processed PDF with GROBID: {pdf_path}")
            return response.text
        except httpx.TimeoutException:
            print(f"GROBID request timed out for {pdf_path}.")
            return ""
        except httpx.ConnectError as e:
            print(f"Could not connect to GROBID server at {self._client.base_url}. Is it running? Error: {e}")
            return ""
        except httpx.RequestError as e:
            print(f"Error calling GROBID API for {pdf_path}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"GROBID Response Status Code: {e.response.status_code}")
                print(f"GROBID Response Text: {e.response.text[:500]}...")
            return ""
        except Exception as e:
            print(f"An unexpected error occurred during GROBID processing for {pdf_path}: {e}")
            return ""
