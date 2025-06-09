import csv
import json
import logging
import os
import re
from typing import Optional, Tuple, List, Dict, Any

from pathlib import Path
import camelot
import pandas as pd
import pdfplumber


class PDFConvertorV3:
    def __init__(self):
        self.activities_patterns = [
            re.compile(r"Schedule\s+of\s+Activities", re.IGNORECASE),
            re.compile(r"Schedule\s+of\s+Activities\s+(SoA)", re.IGNORECASE),
            re.compile(r"Study\s+Schedule", re.IGNORECASE),
            re.compile(r"Protocol\s+Schedule", re.IGNORECASE),
            re.compile(r"Activity\s+Schedule", re.IGNORECASE),
            re.compile(r"Procedure\s+Schedule", re.IGNORECASE),
            re.compile(r"Visit\s+Schedule", re.IGNORECASE),
            re.compile(r"Schedule\s+of\s+Events", re.IGNORECASE),
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

    def _find_actions_pages(self, pages_text: List[str]) -> List[Tuple[int, str]]:
        results = []
        for page_num, text in enumerate(pages_text):
            for pattern in self.activities_patterns:
                if pattern.search(text):
                    results.append((page_num+1, text))  # +1: pages are started from 1, but enym from 0
        return results


    def _extract_tables_with_camelot(self, pdf_path: str, page_num: int) -> Dict[int, pd.DataFrame]:
        tables = {}
        try:
            extracted_tables = camelot.read_pdf(pdf_path, pages=str(page_num))

            # table contains more then 3 column, keep it
            for table in extracted_tables:
                if table.df.shape[1] > 3:
                    tables[page_num] = table.df.map(lambda x: self._clean_cell_value(x))

            # if table is found try to expand to the next page
            if tables:
                next_tables = self._extract_tables_with_camelot(pdf_path, page_num+1)
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

    def _identify_schedule_table(self, table: pd.DataFrame) -> Optional[pd.DataFrame]:
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

        x_count = table_text.count(' x ') + table_text.count('x\n') + table_text.count('\nx')
        if x_count >= 5:
            score += 3

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
        In pdf table might have columns headers occupying several rows.
        Identify them and then we can join then into one cell later on
        """
        table_ref = tables[0]
        results = []
        for i in range(1, len(tables)):
            current_df = tables[i]
            min_rows = min(len(table_ref), len(current_df))
            similar_count = 0
            for j in range(min_rows):
                try:
                    ref_row_str = ' '.join(table_ref.iloc[j].astype(str)).lower()
                    current_row_str = ' '.join(current_df.iloc[j].astype(str)).lower()
                    if ref_row_str == current_row_str:
                        similar_count += 1
                    else:
                        break
                except Exception as err:
                    print(err)

            results.append(similar_count)

        return results

    def _merge_tables_skip_headers(self, tables: List[pd.DataFrame], header_count: int = 3) -> pd.DataFrame:
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

    def _find_only_continuous_and_schedule_tables(self, tables: Dict[int, pd.DataFrame]) -> List[pd.DataFrame]:
        """
        If the previous page (last_page) contained a schedule table (found == True)
        and the current page is immediately after (page_num - 1 == last_page),
        assume the table is a continuation of the previous schedule table

        If pages are not consecutive, reset the found flag.
        """

        last_page = 0
        schedule_tables = []
        found = False
        for page_num in sorted(tables.keys()):
            if found and page_num - 1 == last_page:
                schedule_tables.append(tables[page_num])
                last_page = page_num
            else:
                found = False

            if self._identify_schedule_table(tables[page_num]):
                if not found:
                    schedule_tables.append(tables[page_num])
                last_page, found = page_num, True

        return schedule_tables

    def _save_to_json(self, data: dict, output_path: str):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Result saved in : {output_path}")
        except Exception as e:
            print(f"Error saving JSON: {e}")



    '''
    def _parse_pdf(self, pdf_path: str, output_path: str):
        # get text from PDF by pages
        pages_text = self._extract_text_with_pdfplumber(pdf_path)
        if not pages_text:
            print("Failed to extract text from PDF")
            return False

        # extract all tables from this text
        all_tables = {}
        for page_num, page_text in self._find_schedule_section(pages_text):
            print(f"   SoA mentioning was found on page {page_num + 1}")

            if page_num in all_tables.keys():
                continue

            camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num)
            # try next page too
            if not camelot_tables:
                camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num+1)

            all_tables.update(camelot_tables)

        print(f"   Found {len(all_tables)} tables")

        schedule_tables = self._find_schedule_tables(all_tables)
        if not schedule_tables:
            print("Schedule table not identified")
            return False

        print("Schedule table identified")

        headers = self._find_header_rows(schedule_tables)

        headers_row_count = headers[0] if headers else 0
        merged_schedule_table = self._merge_tables_skip_headers(schedule_tables, headers_row_count)

        merged_df = self._merge_rows_and_rename_columns(merged_schedule_table, headers_row_count)
        merged_df.to_csv(output_path + '.csv', index=False, quotechar='"', quoting=csv.QUOTE_ALL)
        # result = self._parse_schedule_table(pdf_path, merged_df, headers_row_count)
        # self._save_to_json(result, output_path + '.json')

        return "\n\n                                     --- PAGE ---\n".join(pages_text)
        '''

    def extract_text_pages_from_pdf(self, pdf_path: str, output_dir: str) -> List[str]:
        pages_text = self._extract_text_with_pdfplumber(pdf_path)
        if not pages_text:
            print("     Failed to extract text from PDF")
            return False

        return pages_text


    def extract_tables_from_pdf(self, pdf_path: str, output_dir: str) -> pd.DataFrame:
        ### 0: find pages with Activities mentioning
        pages_text = self._extract_text_with_pdfplumber(pdf_path)
        action_mentioned_pages: List[Tuple[int, str]] = self._find_actions_pages(pages_text)
        action_pages_list = [n for n, s in action_mentioned_pages]

        ### 1: extract all RAW tables with action mentioning
        all_tables = {}
        for page_num in action_pages_list:
            print(f"   SoA mentioning on  {page_num} page was found...", end='')
            if page_num in all_tables.keys():
                continue

            camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num)
            # try next page too
            if not camelot_tables:
                camelot_tables = self._extract_tables_with_camelot(pdf_path, page_num + 1)

            print(f'.. {len(camelot_tables)} tables were found with more then 3 columns.')

            all_tables.update(camelot_tables)

        print(f"   Found {len(all_tables)} tables")

        ## 2: Sanity check: are table continuous and about scheduling?
        schedule_tables = self._find_only_continuous_and_schedule_tables(all_tables)
        if not schedule_tables:
            print("   Table are either not contonous of not about scheduling")
            return False
        print("Schedule table identified")

        # TODO: sometime tables are joined by extending to the right , not top-down - need tp handle this case

        ## 3: Identify headers
        headers = self._find_header_rows_numbers(schedule_tables)
        headers_row_count = headers[0] if headers else 0
        print(f'  first {headers_row_count} rows are identified as table header')

        merged_schedule_table = self._merge_tables_skip_headers(schedule_tables, headers_row_count)

        merged_df = self._merge_rows_and_rename_columns(merged_schedule_table, headers_row_count)

        return merged_df