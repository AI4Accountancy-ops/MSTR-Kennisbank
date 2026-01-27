import re
from typing import List
from urllib.parse import urlparse


class FormatHelper:
    @staticmethod
    def extract_label_from_url(url: str) -> str:
        """
        Extracts a human-readable label from a URL for display purposes.

        Args:
            url (str): The URL from which to extract the label.

        Returns:
            str: A formatted label derived from the URL, or "Link" if extraction fails.
        """
        path = re.split(r'/+', url)
        for part in reversed(path):
            if part and not part.startswith("www") and len(part) > 3:
                return part.replace("_", " ").title()
        return "Link"

    @staticmethod
    def extract_domain_label(url: str) -> str:
        """
        Extracts a human-readable label from a URL for display purposes.
        """

        # If the URL contains "belastingdienst.nl", use the original logic.
        if "belastingdienst.nl" in url:
            path_parts = re.split(r'/+', url)
            for part in reversed(path_parts):
                if part and not part.startswith("www") and len(part) > 3:
                    return "Belastingdienst - " + part.replace("_", " ").title()
            return "Link"

        # Custom extraction for other URLs.
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Special rule for Nextens URLs.
        if "nextens.nl" in netloc:
            path_segments = [segment for segment in parsed_url.path.split("/") if segment]
            if path_segments:
                return f"Nextens {path_segments[0].replace('_', ' ').title()}"
            else:
                return "Nextens"

        if "mfas.nl" in netloc:
            return "MFAS"

        if "indicator.nl" in netloc:
            return "Indicator"

        # Default: return the first part of the domain with the first letter capitalized.
        first_part = netloc.split('.')[0]
        return first_part.capitalize() if first_part else "Link"

    @staticmethod
    def remove_duplicate_urls(urls: List[str]) -> List[str]:
        """
        Remove duplicate URLs from the list, considering both labels and URLs, while preserving the order.

        Args:
            urls (List[str]): A list of URLs or formatted strings in Markdown format.

        Returns:
            List[str]: A list of unique URLs in the original order.
        """
        seen_labels = set()
        unique_urls = []
        for url in urls:
            # Extract the label inside the square brackets
            label_match = re.match(r'\[(.*?)\]', url)
            if label_match:
                label = label_match.group(1)
                # Check if the label has already been seen
                if label not in seen_labels:
                    unique_urls.append(url)
                    seen_labels.add(label)
            else:
                # If no label is found, handle it as a normal URL
                if url not in unique_urls:
                    unique_urls.append(url)

        return unique_urls

    @staticmethod
    def preprocess_latex(expression: str) -> str:
        """
        Preprocess LaTeX to ensure proper formatting and escaping within LaTeX content.
        Escapes special characters only if they are not already escaped.
        """
        # Define patterns for characters that need to be escaped
        special_chars = {
            "&": r"\&",
            "#": r"\#",
            "_": r"\_",
            "%": r"\%",
        }

        # Iterate over each special character
        for char, escaped_char in special_chars.items():
            # Use negative lookbehind to ensure the character is not already escaped
            pattern = rf"(?<!\\){re.escape(char)}"
            expression = re.sub(pattern, escaped_char, expression)

        return expression

    @staticmethod
    def process_latex_blocks_and_inline(text: str) -> str:
        """
        Detect and preprocess LaTeX blocks (`$$...$$`) and inline LaTeX (`$...$`) separately.
        """
        # Patterns for inline and block LaTeX
        inline_latex_pattern = r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)"
        block_latex_pattern = r"\$\$(.+?)\$\$"

        def preprocess_inline(match):
            content = match.group(1)
            return f"${FormatHelper.preprocess_latex(content.strip())}$"

        def preprocess_block(match):
            content = match.group(1)
            return f"$$\n{FormatHelper.preprocess_latex(content.strip())}\n$$"

        # Process block-level LaTeX first
        text = re.sub(block_latex_pattern, preprocess_block, text, flags=re.DOTALL)

        # Process inline LaTeX
        text = re.sub(inline_latex_pattern, preprocess_inline, text)

        return text

    @staticmethod
    def trim_indented_latex(text: str) -> str:
        """
        Remove unnecessary indentation from LaTeX block delimiters.
        """
        return re.sub(r"^\s*\$\$", "$$", text, flags=re.MULTILINE)

    def sanitize_markdown(self, llm_response: str) -> str:
        """
        Processes a Markdown response from the LLM.
        Ensures proper formatting by sanitizing LaTeX content without converting to HTML.
        """
        llm_response = self.process_latex_blocks_and_inline(llm_response)
        llm_response = self.trim_indented_latex(llm_response)
        return llm_response