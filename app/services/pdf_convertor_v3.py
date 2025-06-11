import logging
import re
from typing import Optional, Tuple, List, Dict, Any
from difflib import SequenceMatcher

import camelot
import pandas as pd
import pdfplumber


class PDFConvertorV3:
    def __init__(self):
        self.activities_patterns = [
            re.compile(r"Schedule\s+of\s+Activities", re.IGNORECASE),
            re.compile(r"Schedule\s+of\s+Activities\s+(SoA)", re.IGNORECASE),
            re.compile(r"Study\s+Schedule+\sProtocol", re.IGNORECASE),
            re.compile(r"Protocol\s+Schedule", re.IGNORECASE),
            re.compile(r"Activity\s+Schedule", re.IGNORECASE),
            re.compile(r"Procedure\s+Schedule", re.IGNORECASE),
            #re.compile(r"Visit\s+Schedule", re.IGNORECASE),
            re.compile(r"Schedule\s+of\s+Events", re.IGNORECASE),
        ]

        self.objectives_patterns = [
            re.compile(r"Objectives\s+and\s+Endpoints", re.IGNORECASE),
            re.compile(r"Study\s+Objectives", re.IGNORECASE),
            re.compile(r"Primary\s+and\s+Secondary\s+Objectives", re.IGNORECASE),
            re.compile(r"Objectives\s+&\s+Endpoints", re.IGNORECASE),
            re.compile(r"Study\s+Endpoints", re.IGNORECASE),
            re.compile(r"Primary\s+Objectives", re.IGNORECASE),
        ]

    def _extract_text_with_pdfplumber(self, pdf_path:str) -> List[str]:
        pages_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
        except Exception as e:
            print(f"Error extracting text with pdfplumber: {e}")
        return pages_text

    def _find_pages_by_pattern(self, pages_text: List[str], patterns: List[re.Pattern]) -> List[Tuple[int, str]]:
        results = []
        for page_num, text in enumerate(pages_text):
            for pattern in patterns:
                if pattern.search(text):
                    results.append((page_num+1, text))  # +1: pages are started from 1, but enym from 0
        return results


    def _extract_tables_with_camelot(self, pdf_path: str, page_num: int, min_table_col: int) -> Dict[int, pd.DataFrame]:
        tables = {}
        try:
            extracted_tables = camelot.read_pdf(pdf_path, pages=str(page_num))
            #TODO: move table checking outside
            #table contains more than min_table_col column, keep it
            for table in extracted_tables:
                if table.df.shape[1] > min_table_col:
                    tables[page_num] = table.df.map(lambda x: self._clean_cell_value(x))
                else:
                    print(f'    A [Table] was found with less then {min_table_col} column, skipped')

            # if table is found try to expand to the next page with recursion
            if tables:
                next_tables = self._extract_tables_with_camelot(pdf_path, page_num+1, min_table_col)
                tables.update(next_tables)

        except Exception as e:
            print(f"Error in camelot: {e}")

        return tables


    def _clean_cell_value(self, value) -> str:
        if pd.isna(value) or value is None:
            return ""

        cleared_text = str(value).strip()
        cleared_text = re.sub(r'\s+', ' ', cleared_text)
        cleared_text = re.sub(r'\xa0', ' ', cleared_text) # Remove all NBSP
        cleared_text = re.sub(r'\s+([.,!?;:])', r'\1', cleared_text)
        cleared_text = re.sub('\t+', ' ', cleared_text)
        cleared_text = re.sub('\n+', ' ', cleared_text)
        cleared_text = re.sub(' +', ' ', cleared_text)

        return cleared_text.strip()

    def _is_schedule_table_heuristic(self, table: pd.DataFrame) -> bool:
        schedule_indicators = [
            'procedure', 'day', 'week', 'screening', 'period', 'follow', 'study'
        ]

        score = 0
        table_text = table.to_string().lower()
        for indicator in schedule_indicators:
            if indicator in table_text:
                score += 1

        if len(table.columns) >= 4:
            score += 2

        if len(table) >= 3:
            score += 1

        # counting a checkmark in the table.. craze heuristic - remove it !
        x_count = table_text.count(' x ') + table_text.count('x\n') + table_text.count('\nx')
        if x_count >= 5:
            score += 3

        return score >= 5


    def _is_objectives_table_heuristic(self, table: pd.DataFrame) -> bool:
        """
        It is crazy appoach - change it.
        May be use a simple classifier
        """
        objectives_words = [
            'objectives', 'endpoints', 'primary'
        ]

        score = 0
        table_text = table.to_string().lower()
        for indicator in objectives_words:
            if indicator in table_text:
                score += 1

        if len(table.columns) == 2:
            score += 2

        return score >= 5


    def _fill_rows_with_previous(self, table: pd.DataFrame, rows_count: int) -> pd.DataFrame:
        result_df = table.copy()
        for n in range(rows_count):
            selected_row = result_df.iloc[n]
            for i in range(1, len(selected_row)):
                current_value = selected_row.iloc[i]
                previous_value = selected_row.iloc[i - 1]

                if pd.isna(current_value) or not current_value:
                    selected_row.iloc[i] = previous_value

            result_df.iloc[n] = selected_row

        return result_df

    def _merge_rows_and_rename_columns(self, table: pd.DataFrame, rows_to_merge: int) -> pd.DataFrame:

        if rows_to_merge > len(table):
            raise ValueError(
                f"The number of rows to merge ({rows_to_merge}) exceeds the number of rows in the Data Frame ({len(table)})")

        if rows_to_merge <= 0:
            return table

        new_table = self._fill_rows_with_previous(table, 1) if rows_to_merge else 0
        merged_values = {}
        for col in new_table.columns:
            merged_values[col] = ':'.join(map(str, new_table[col].head(rows_to_merge).values))

        result_df = new_table.iloc[rows_to_merge:].copy()

        result_df.columns = [merged_values[col] for col in new_table.columns]

        return result_df


    def _find_header_rows_numbers(self, tables: List[pd.DataFrame]) -> list:
        """
        A pdf table might have columns headers occupying several rows.
        Identify them and then we can join then into one cell later on - CHANGE THIS APPROACH!
        """
        table_ref = tables[0]   # use first table as a reference
        results = []
        for i in range(1, len(tables)): # loop over other tables
            current_df = tables[i]
            min_rows = min(len(table_ref), len(current_df)) # to avoid indexError
            similar_count = 0
            for j in range(min_rows):       # start comparing rows from the top
                try:
                    ref_row_str = ' '.join(table_ref.iloc[j].astype(str)).lower()
                    current_row_str = ' '.join(current_df.iloc[j].astype(str)).lower()
                    if ref_row_str == current_row_str:   #Count how many top rows are identical between the reference and the current table.
                        similar_count += 1
                    else:
                        break  # If a difference is found, stop comparing further rows.
                except Exception as err:
                    print(err)

            results.append(similar_count)

        return results

    def _merge_tables_skip_headers(self, tables: List[pd.DataFrame], header_count: int = 1) -> pd.DataFrame:
        first_columns = set(tables[0].columns)
        for i, df in enumerate(tables[1:], start=1):
            if set(df.columns) != first_columns:
                raise ValueError(f"DataFrame {i} has different columns compared to the first DataFrame")
        merged_df = tables[0].copy()

        for df in tables[1:]:
            if len(df) > header_count:
                merged_df = pd.concat([merged_df, df.iloc[header_count:]], ignore_index=True)
            #else:
                #merged_df = pd.concat([merged_df, df.iloc[0:0]], ignore_index=True)

        return merged_df

    def _only_continuous_and_activity_schedule_tables(self, tables: Dict[int, pd.DataFrame]) -> List[pd.DataFrame]:
        """
        If the previous page (last_page) contained a schedule table (found == True)
        and the current page is immediately after (page_num - 1 == last_page),
        assume the table is a continuation of the previous schedule table

        Returns only those tables that:
            Match schedule heuristics
            Are grouped by page continuity
        """

        last_page = 0
        schedule_tables = []
        found = False
        for page_num in sorted(tables.keys()):
            # If we previously found a schedule table and this page is the next consecutive page
            if found and page_num - 1 == last_page:
                schedule_tables.append(tables[page_num])
                last_page = page_num
            else:
                found = False

            if self._is_schedule_table_heuristic(tables[page_num]):
                if not found:
                    schedule_tables.append(tables[page_num])
                last_page, found = page_num, True

        return schedule_tables


    # def _only_continuous_and_objective_tables(self, tables: Dict[int, pd.DataFrame]) -> List[pd.DataFrame]:
    #     last_page = 0
    #     objective_tables = []
    #     found = False
    #     for page_num in sorted(tables.keys()):
    #         # If we previously found a schedule table and this page is the next consecutive page
    #         if found and page_num - 1 == last_page:
    #             objective_tables.append(tables[page_num])
    #             last_page = page_num
    #         else:
    #             found = False
    #
    #         if self._is_objectives_table_heuristic(tables[page_num]):
    #             if not found:
    #                 objective_tables.append(tables[page_num])
    #             last_page, found = page_num, True
    #
    #     return objective_tables

    def _only_continuous_and_objective_tables(self, tables: Dict[int, pd.DataFrame]) -> List[pd.DataFrame]:
        last_page = -1
        objective_tables = []
        found = False

        for page_num in sorted(tables.keys()):
            current_table = tables[page_num]
            is_objective = self._is_objectives_table_heuristic(current_table)

            # If previous table was valid and this page is consecutive, also require heuristic match
            if found and page_num - 1 == last_page and is_objective:
                objective_tables.append(current_table)
                last_page = page_num
            elif is_objective:
                # New standalone valid table
                objective_tables.append(current_table)
                last_page, found = page_num, True
            else:
                found = False  # Reset if not valid

        return objective_tables


    def _deduplicate_tables(self, tables: List[pd.DataFrame], similarity_threshold: float = 0.95) -> List[pd.DataFrame]:
        """
        Deduplicate tables by comparing their normalized row-wise content using SequenceMatcher.
        """

        def normalize_table(table: pd.DataFrame) -> str:
            # Normalize: strip spaces, lowercase, flatten to single string
            norm_rows = [
                ' | '.join(row.astype(str).str.strip().str.lower().tolist())
                for _, row in table.iterrows()
            ]
            return '\n'.join(norm_rows)

        unique_tables = []
        normalized_cache = []

        for table in tables:
            norm_str = normalize_table(table)

            is_duplicate = False
            for prev_norm in normalized_cache:
                similarity = SequenceMatcher(None, norm_str, prev_norm).ratio()
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_tables.append(table)
                normalized_cache.append(norm_str)

        return unique_tables

    def extract_text_pages_from_pdf(self, pdf_path: str) -> List[str]:
        pages_text = self._extract_text_with_pdfplumber(pdf_path)
        if not pages_text:
            print("     Failed to extract text from PDF")
            return False

        return pages_text



    def extract_activity_tables_from_pdf(self, pdf_path: str) -> Optional[pd.DataFrame]:
        logging.info("Looking for Action tables:")

        min_table_col_allowed = 3

        ### 0: find pages with Activities mentioning
        pages_text = self._extract_text_with_pdfplumber(pdf_path)

        pages_with_pattern: List[Tuple[int, str]] = self._find_pages_by_pattern(pages_text, self.activities_patterns)
        pattern_pages = [n for n, s in pages_with_pattern]

        ### 1: extract all RAW tables with pattern (action)  mentioning
        all_tables = {}
        for page_num in pattern_pages:
            print(f"   XXX mentioning was found  on  {page_num} page...", end='')
            if page_num in all_tables.keys():
                continue

            camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num, min_table_col_allowed)
            # try next page too
            if not camelot_tables:
                camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num + 1, min_table_col_allowed)

            print(f'.. {len(camelot_tables)} tables were found on page {page_num} (with more then 3 columns).')
            all_tables.update(camelot_tables)

        print(f"   Found {len(all_tables)} pattern (Action, Objectives) tables")

        ## 2: Sanity check: are table continuous and about activity scheduling?
        schedule_tables = self._only_continuous_and_activity_schedule_tables(all_tables)
        if not schedule_tables:
            print("   Table are either not contonous of not about scheduling")
            return None
        print("Schedule table identified")

        # TODO: sometime tables are joined by extending to the right , not top-down - need tp handle this case

        ## 3: Identify headers
        headers = self._find_header_rows_numbers(schedule_tables)
        headers_row_count: int = headers[0] if headers else 0
        print(f'  first {headers_row_count} rows are identified as table header')

        merged_schedule_table = self._merge_tables_skip_headers(schedule_tables, headers_row_count)
        merged_df = self._merge_rows_and_rename_columns(merged_schedule_table, headers_row_count)

        return merged_df


    # TODO: it seems like they are identical, refactor that
    def extract_objectives_tables_from_pdf(self, pdf_path: str) -> Optional[pd.DataFrame]:

        min_table_col_allowed = 1

        ### 0: find pages with Pattern mentioning
        pages_text = self._extract_text_with_pdfplumber(pdf_path)

        pages_with_pattern_tuples: List[Tuple[int, str]] = self._find_pages_by_pattern(pages_text, self.objectives_patterns)
        pattern_pages = [n for n, s in pages_with_pattern_tuples]

        ### 1: extract all RAW tables with pattern (action)  mentioning
        all_tables = {}
        for page_num in pattern_pages:
            print(f"   XXX mentioning was found  on  {page_num} page...", end='')
            if page_num in all_tables.keys():
                continue

            camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num, min_table_col_allowed)
            # check the following gaoe with recursion
            if not camelot_tables:
                camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num + 1, min_table_col_allowed)  # recursion

            print(f'.. {len(camelot_tables)} tables were found on page {page_num} (with more then 3 columns).')
            all_tables.update(camelot_tables)

        print(f"     Total  {len(all_tables)} table were found  (with Action or Objectives)")

        ## 2: Sanity check: are tables continuous and about scheduling?
        objective_tables = self._only_continuous_and_objective_tables(all_tables)
        if not objective_tables:
            print("   Tables are either not continuos of not about objectives")
            return None
        print("Objective and endpoint table identified")

        # TODO: sometime tables are joined by extending to the right , not top-down - need tp handle this case

        objective_tables_dedup = self._deduplicate_tables(objective_tables)

        ## 3: Identify headers
        headers_row_count = 1   # we know that objective is a small table with simple headers

        print(f'  first {headers_row_count} rows are identified as table header')

        merged_schedule_table = self._merge_tables_skip_headers(objective_tables_dedup, headers_row_count)
        merged_df = self._merge_rows_and_rename_columns(merged_schedule_table, headers_row_count)

        return merged_df

