import concurrent.futures
import json
import re
from datetime import datetime
from typing import BinaryIO, List, Dict, Set, Optional, Iterator, Union, Tuple
from urllib.parse import urlparse, unquote

import html2text
import requests
from ddgs import DDGS
from bs4 import BeautifulSoup

import definitions.names as n
from config.settings import get_settings
from definitions.credentials import Credentials
from definitions.enums import ToggleVectorSearch, FiscalTopic
from prompts import system_prompt_templates, user_prompt_templates
from prompts.system_prompt_templates import question_system_prompt, search_query_system_prompt, extra_sources_needed_system_prompt
from prompts.user_prompt_templates import question_user_prompt, search_query_user_prompt, extra_sources_needed_user_prompt
from response_models.chat_response_models import TaxQueryResponse, ChunkInfo, QuestionFiscalTopicYear, SearchQueryResponse, ExtraSourcesNeeded
from services.assistants_factory import AssistantsFactory
from services.llm_factory import LLMFactory
from services.vector_store import VectorStore
from utils.format_helper import FormatHelper
from logger.logger import Logger



logger = Logger.get_logger(__name__)


class QueryHandler:
    def __init__(self):
        self.llm = LLMFactory(n.AZURE_OPENAI)
        self.assistants_factory = AssistantsFactory()
        self.vector_store = VectorStore()
        self.settings = get_settings()
        self.format_helper = FormatHelper()
        # Domains to exclude entirely from search results (add NSFW and unrelated)
        self.blocked_hosts = [
            "wikipedia.org",
            "wiktionary.org",
            "wikibooks.org",
            "wikidata.org",
            "wikiwand.com",
        ]
        # Preferred authoritative NL domains (ordered by priority)
        self.authority_hosts = [
            "belastingdienst.nl",
            "wetten.overheid.nl",
            "overheid.nl",
            "rijksoverheid.nl",
            "tweedekamer.nl",
            "zoek.officielebekendmakingen.nl",
            "kvk.nl",
        ]
        # Hosts that are search engines or meta-search result pages (skip entirely)
        self.search_engine_hosts = [
            "google.", "bing.", "duckduckgo.", "ddg.", "brave.", "yahoo.", "yandex.", "ecosia.",
        ]

    def _is_nl_host(self, host: str) -> bool:
        try:
            h = host.lower()
            if h.startswith("www."):
                h = h[4:]
            return h.endswith(".nl") or any(ah in h for ah in self.authority_hosts)
        except Exception:
            return False

    def _is_dutch_text(self, text: str) -> bool:
        """Very light heuristic to filter out non-Dutch pages without heavy language models.
        - Reject if many CJK/Hangul characters (e.g., Japanese/Korean).
        - Prefer if contains common Dutch tokens.
        """
        if not text or len(text) < 200:
            return False
        total = len(text)
        if total == 0:
            return False
        # Detect presence of CJK/Hangul characters
        cjk = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", text)
        if len(cjk) / total > 0.05:  # >5% CJK/Hangul → likely not Dutch
            return False
        tokens = [" de ", " het ", " en ", " voor ", " artikel ", " belasting", " wet "]
        t = " " + text.lower() + " "
        return any(tok in t for tok in tokens)

    def process_question(self, user_message: str, chat_history: Optional[list] = None) -> QuestionFiscalTopicYear:
        """
        Processes the user message
        """
        try:
            # Initialize system prompt
            system_prompt = question_system_prompt

            # Single LLM call to extract fiscal topics, years, vector_query
            user_prompt = question_user_prompt.format(
                query=user_message,
                chat_history=chat_history
            )

            response = self.llm.normal_completion(
                response_model=QuestionFiscalTopicYear,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model="gpt-4.1-mini"
            )

            return response

        except Exception as e:
            logger.error(f"Error processing questions: {e}")
            raise e

    def check_if_extra_sources_needed(self, user_message: str, chat_history: Optional[list] = None, chunks_str: Optional[str] = None):
        """
        Return True if we should fetch extra web sources before answering.

        Uses a tiny model for a fast sufficiency check based on the question,
        brief chat history, and compact chunk metadata.
        """
        try:
            system_prompt = extra_sources_needed_system_prompt

            # Normalize inputs for safety and token efficiency
            safe_query = (user_message or "").strip()
            safe_history = chat_history or {}
            safe_chunks = chunks_str
            if not isinstance(safe_chunks, str):
                try:
                    safe_chunks = json.dumps(safe_chunks or [])
                except Exception:
                    safe_chunks = "[]"

            user_prompt = extra_sources_needed_user_prompt.format(
                query=safe_query,
                chat_history=safe_history,
                chunks_str=safe_chunks,
            )

            response = self.llm.normal_completion(
                response_model=ExtraSourcesNeeded,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model="gpt-4.1-mini",
            )

            # Primary field per response model
            value = getattr(response, "extra_sources_needed", None)
            # Be tolerant if prompt/schema variations use a different key
            if value is None:
                value = getattr(response, "extra_sources_needed", None)
            return bool(value)

        except Exception as e:
            logger.warning(f"Extra-sources sufficiency check failed; defaulting to False: {e}")
            return False

    def _serialize_chunk(self, chunk):
        """Convert a ChunkInfo object or any custom object to a dictionary."""
        try:
            if hasattr(chunk, '__dict__'):
                # If it's a custom object with attributes
                return {k: self._serialize_chunk(v) for k, v in chunk.__dict__.items() if not k.startswith('_')}
            elif isinstance(chunk, (list, tuple)):
                # If it's a list or tuple
                return [self._serialize_chunk(item) for item in chunk]
            elif isinstance(chunk, dict):
                # If it's already a dictionary
                return {k: self._serialize_chunk(v) for k, v in chunk.items()}
            elif hasattr(chunk, 'isoformat') and callable(chunk.isoformat):
                # Handle datetime objects
                return chunk.isoformat()
            else:
                # Return basic types as is
                return chunk
        except Exception as e:
            logger.error(f"Error serializing chunk: {e}")
            # Return a safe default
            return None

    def answer_tax_query(
            self,
            user_message: str,
            vector_query: str,
            tone_of_voice: str,
            year: List[int],
            fiscal_topic: List[str],
            chat_history: Optional[list] = None,
    ) -> Iterator[Union[str, dict]]:
        """
        Handle tax-related queries by searching relevant data chunks, formatting them,
        generating a prompt for the language model, and streaming the response.
        
        Args:
            user_message: The user's question
            tone_of_voice: The desired tone for the response
            year: List of years the question relates to
            fiscal_topic: List of fiscal topics (e.g., ['BTW', 'IB'])
            reasoning_effort: The level of reasoning effort to apply
            chat_history: Optional chat history for context
        """
        # Initialize with empty chat history if none provided
        if chat_history is None:
            chat_history = []
        relevant_history = self._extract_relevant_chat_history(chat_history)

        # Single unified path: perform vector search and optionally web augment based on explicit flag
        try:
            toggle_vector_search = Credentials.get_toggle_vector_search()
            vector_search_enabled = toggle_vector_search == ToggleVectorSearch.ON.value
        except Exception:
            vector_search_enabled = True

        retrieval_performed = vector_search_enabled

        if retrieval_performed:
            # Perform retrieval and then signal completion
            # For medium/high, limit initial retrieval to 7
            all_raw_chunks, formatted_dict = [], {}
            # If topic is Onbekend, don't pass restrictive topic filters
            effective_topics = [] if (len(fiscal_topic) == 1 and fiscal_topic[0] == FiscalTopic.ONBEKEND.value) else fiscal_topic
            chunks = self._retrieve_and_prepare_chunks(vector_query, year, effective_topics, initial_limit=7)
            if chunks:
                formatted_dict = self._format_chunks_as_dict(user_message, chunks)
                all_raw_chunks = chunks
            # Do NOT stop spinner yet; we will analyze/augment before signaling docs_retrieved
        else:
            # Skip retrieval entirely (e.g., topic is Onbekend or toggle off)
            all_raw_chunks, formatted_dict = [], {}

        sources_block = ""

        # UI: show analyzing sources spinner
        try:
            yield n.ANALYZING_SOURCES_FLAG
        except Exception:
            pass
        # Decide whether extra web sources are needed (fast sufficiency check)
        try:
            chunks_meta_str = json.dumps([formatted_dict], ensure_ascii=False) if formatted_dict else "[]"
        except Exception:
            chunks_meta_str = "[]"
        need_extra = False
        try:
            need_extra = (len(all_raw_chunks) <= 2) or self.check_if_extra_sources_needed(
                user_message=user_message,
                chat_history=relevant_history,
                chunks_str=chunks_meta_str,
            )
        except Exception:
            need_extra = len(all_raw_chunks) == 0

        # If needed (or explicitly requested), augment with top 3 web sources
        used_web_urls: List[str] = []
        if need_extra:
            # UI: show retrieving additional sources spinner
            try:
                yield n.RETRIEVING_MORE_SOURCES_FLAG
            except Exception:
                pass
            try:
                sources_block, selected_urls = self._retrieve_top_web_sources(
                    question=user_message,
                    chat_history=relevant_history,
                    target_count=3,
                )
                used_web_urls = selected_urls[:1]
            except Exception as e:
                logger.warning(f"Web augmentation failed: {e}")

        # After analysis/optional augmentation, signal retrieval finished for the UI
        try:
            yield {"flag": "docs_retrieved"}
        except Exception:
            pass

        # Build user prompt with both chunks and optional web sources
        user_prompt = user_prompt_templates.tax_query_user_prompt.format(
            chat_history=relevant_history,
            query=user_message,
            tone_of_voice=tone_of_voice,
            chunks_str=[formatted_dict],
            sources_block=sources_block,
        )

        try:            
            # Instead of getting the complete answer at once, we'll stream it
            # and track which chunks are used
            current_full_answer = ""
            used_chunk_ids = set()
            
            # Stream from LLM with a fixed model and the provided reasoning effort
            model_name = "gpt-5"
            reasoning = "low"

            for partial_response in self.llm.stream_completion(
                response_model=TaxQueryResponse,
                messages=[
                    {"role": "system", "content": system_prompt_templates.tax_query_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                reasoning_effort=reasoning,
                model=model_name,
            ):
                # 1) Handle partial text
                if hasattr(partial_response, 'answer') and partial_response.answer:
                    partial_answer = partial_response.answer
                    # Use the new DMP-based helper to find newly appended text:
                    new_content = self._get_new_text_suffix_prefix(current_full_answer, partial_answer)

                    if new_content:
                        yield new_content
                        current_full_answer += new_content

                # 2) Handle chunk usage info, if any
                if hasattr(partial_response, 'chunks') and partial_response.chunks:
                    chunks_data = partial_response.chunks
                    if not isinstance(chunks_data, list):
                        chunks_data = [chunks_data]
                    for chunk_info in chunks_data:
                        if getattr(chunk_info, 'used', False):
                            chunk_id = getattr(chunk_info, 'chunk_id', None)
                            if chunk_id:
                                used_chunk_ids.add(chunk_id)

            # Prepare and return the final response with used chunks
            yield from self._prepare_final_response(
                current_full_answer, used_chunk_ids, all_raw_chunks, additional_web_urls=used_web_urls
            )

        except Exception as e:
            logger.error(f"Error getting response from LLM: {e}")
            yield {"flag": "error", "message": "Er is een fout opgetreden bij het verwerken van uw aanvraag."}
            return

    def generate_search_query(self, question: str, chat_history: Optional[list]) -> str:
        """
        Use the LLM to produce a strong Dutch web search query from the question and chat history.
        """
        try:
            system_prompt = search_query_system_prompt
            user_prompt = search_query_user_prompt.format(
                question=(question or "").strip(),
                chat_history=json.dumps(chat_history or {}, ensure_ascii=False)
            )

            response = self.llm.normal_completion(
                response_model=SearchQueryResponse,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model="gpt-4.1-mini",
            )

            search_query = (response.search_query or "").strip()
            if not search_query:
                return (question or "").strip()
            return search_query
        except Exception as e:
            logger.warning(f"Falling back to raw question for search query due to error: {e}")
            return (question or "").strip()

    def _format_sources_as_markdown(self, sources: List[str]) -> List[str]:
        """Convert a list of raw URLs or mixed strings into markdown links with readable titles."""
        formatted: List[str] = []
        markdown_re = re.compile(r"^\[[^\]]+\]\([^\)]+\)$")
        seen_urls: Set[str] = set()

        for src in sources:
            if not isinstance(src, str) or not src.strip():
                continue
            s = src.strip()
            # If already a markdown link, keep as-is
            if markdown_re.match(s):
                formatted.append(s)
                continue
            # If it looks like a URL, synthesize a display label
            if s.startswith("http://") or s.startswith("https://"):
                try:
                    parsed = urlparse(s)
                    host = parsed.netloc.replace("www.", "").strip()
                    path_part = parsed.path.strip("/")
                    # Skip homepages or empty paths – we require specific pages
                    if not path_part:
                        continue
                    last_segment = unquote(path_part.split("/")[-1]) if path_part else ""
                    # Prefer last non-empty segment
                    if not last_segment and path_part:
                        segments = [seg for seg in path_part.split("/") if seg]
                        last_segment = unquote(segments[-1]) if segments else ""

                    def prettify(text: str) -> str:
                        text = re.sub(r"[-_]+", " ", text)
                        text = re.sub(r"\s+", " ", text).strip()
                        # Title-case but keep common lowercase words short if mid-sentence
                        return text.title()

                    # Compute display host without TLDs (e.g., belastingdienst.nl -> Belastingdienst)
                    raw_host = host.split(":")[0]
                    host_parts = [p for p in raw_host.split(".") if p]
                    base_domain = host_parts[-2] if len(host_parts) >= 2 else host_parts[0] if host_parts else raw_host
                    site_label = prettify(base_domain)
                    topic_label = prettify(last_segment) if last_segment else ""

                    if not topic_label:
                        # If last segment is empty after sanitization, skip (likely homepage)
                        continue
                    # Example: "Belastingdienst – Zelfstandigenaftrek"
                    label = f"{site_label} – {topic_label}"

                    final_url = s
                    if final_url in seen_urls:
                        continue
                    seen_urls.add(final_url)
                    formatted.append(f"[{label}]({final_url})")
                    continue
                except Exception:
                    pass

            # Fallback: wrap raw text if not a URL
            formatted.append(s)

        return formatted

    def _postprocess_sources(self, sources: List[str]) -> List[str]:
        """Apply strict filtering and normalization to raw URLs returned by the model.

        Rules:
        - Keep only absolute http(s) URLs
        - Drop homepages (no path or /)
        - Deduplicate preserving order
        - Trim whitespace
        - Optionally fix common typos in known domains/segments
        """
        cleaned: List[str] = []
        seen: Set[str] = set()

        def fix_common_typos(u: str) -> str:
            try:
                p = urlparse(u)
                path = p.path
                # Fix common typo: op-houdt -> ophoudt
                path = path.replace("/op-houdt-", "/ophoudt-")
                # Normalize duplicate slashes
                path = re.sub(r"/+", "/", path)
                return f"{p.scheme}://{p.netloc}{path}{('?' + p.query) if p.query else ''}"
            except Exception:
                return u

        for s in sources:
            if not isinstance(s, str):
                continue
            s = s.strip()
            if not (s.startswith("http://") or s.startswith("https://")):
                continue
            try:
                p = urlparse(s)
                if not p.path or p.path == "/":
                    continue
                # Exclude direct PDF links (case-insensitive)
                try:
                    if p.path.lower().endswith(".pdf"):
                        continue
                except Exception:
                    pass
                # Exclude search engine result pages entirely
                host_l = p.netloc.lower()
                if host_l.startswith("www."):
                    host_l = host_l[4:]
                if any(se in host_l for se in self.search_engine_hosts):
                    continue
                # Exclude on-site search result pages and framework invalidation URLs
                q_l = (p.query or '').lower()
                path_l = (p.path or '').lower()
                if (
                    '/search' in path_l or 'zoeken' in path_l or 'search-results' in path_l or
                    'q=' in q_l or 'engine=' in q_l or 'sveltekit' in q_l or 'sveltekit' in path_l
                ):
                    # Allow exceptions for known document patterns on overheid domains
                    allow = False
                    if 'zoek.officielebekendmakingen.nl' in host_l:
                        # Keep only document pages (simple heuristics)
                        if any(seg in path_l for seg in ['kst-', 'stcrt-', 'kb-', '/dossier/', '/regeling/']):
                            allow = True
                    if not allow:
                        continue
            except Exception:
                continue
            s = fix_common_typos(s)
            if s in seen:
                continue
            seen.add(s)
            cleaned.append(s)
        # Exclude blocked hosts, and then prioritize allowlist
        filtered: List[str] = []
        for u in cleaned:
            try:
                host = urlparse(u).netloc.lower()
                # Remove leading 'www.' for consistent matching
                if host.startswith("www."):
                    host = host[4:]
                if any(bh in host for bh in self.blocked_hosts):
                    continue
                filtered.append(u)
            except Exception:
                # If parsing fails, keep conservative and skip the URL
                continue
        # Stable priority sort: prefer authority hosts, keep original order within same priority
        def priority(u: str) -> int:
            try:
                host = urlparse(u).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                for idx, ah in enumerate(self.authority_hosts):
                    if ah in host:
                        return idx
                return len(self.authority_hosts) + 1
            except Exception:
                return len(self.authority_hosts) + 2

        return sorted(filtered, key=priority)

    def _verify_urls(self, urls: List[str]) -> List[str]:
        """Keep only URLs that respond with 2xx/3xx and are not blocked; prefer authority hosts."""
        verified: List[str] = []
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"}
        visited: Set[str] = set()
        for u in urls:
            try:
                # Blocked hosts quick check
                host = urlparse(u).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                if any(bh in host for bh in self.blocked_hosts):
                    continue
                if any(se in host for se in self.search_engine_hosts):
                    continue

                # Prefer HEAD for speed; some sites block it → fall back to GET
                resp = session.head(u, headers=headers, timeout=2, allow_redirects=True)
                if resp.status_code >= 400 or resp.status_code < 200:
                    # Skip retry if we already got this host/path recently with auth/rate/404
                    if resp.status_code in (401, 403, 404, 429):
                        visited.add(u)
                        continue
                    resp = session.get(u, headers=headers, timeout=4, allow_redirects=True)

                if 200 <= resp.status_code < 400:
                    final_u = resp.url or u
                    # Avoid duplicate final URLs
                    if final_u not in visited:
                        visited.add(final_u)
                        verified.append(final_u)
            except Exception:
                continue

        # Stable priority sort favoring authority hosts
        def priority(u: str) -> int:
            try:
                host = urlparse(u).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                for idx, ah in enumerate(self.authority_hosts):
                    if ah in host:
                        return idx
                return len(self.authority_hosts) + 1
            except Exception:
                return len(self.authority_hosts) + 2

        return sorted(verified, key=priority)

    def _fetch_and_parse_pages(self, urls: List[str], max_pages: int = 3) -> List[Dict[str, str]]:
        """Fetch and parse pages concurrently with early-stop once we have 3 good pages.

        Returns a list of dicts: {url, title, text}
        """
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        }

        # Oversample and early-stop: allow up to 12 fetches but stop once we have 3 good pages
        limited = urls[:12]

        def fetch(u: str) -> Optional[Dict[str, str]]:
            try:
                r = session.get(u, headers=headers, timeout=4)
                if r.status_code >= 400:
                    return None
                html = r.text
                soup = BeautifulSoup(html, "html.parser")
                # Remove noisy elements
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()
                title = (soup.title.string if soup.title and soup.title.string else "").strip()

                # Prefer semantically relevant containers
                candidates = []
                # 1) <main>
                m = soup.find("main")
                if m:
                    candidates.append(m)
                # 2) role="main"
                role_main = soup.find(attrs={"role": "main"})
                if role_main:
                    candidates.append(role_main)
                # 3) <article>
                art = soup.find("article")
                if art:
                    candidates.append(art)
                # 4) Common id/class names that often contain article content
                common_selectors = [
                    {"id": re.compile(r"content|main|artikel|article", re.I)},
                    {"class": re.compile(r"content|article|post|rich|kg-", re.I)},
                ]
                for sel in common_selectors:
                    el = soup.find(attrs=sel)
                    if el:
                        candidates.append(el)

                # 5) Fallback: choose the largest text block among top-level sections/divs
                if not candidates:
                    blocks = soup.find_all(["section", "div"], limit=50)
                    best_el, best_len = None, 0
                    for b in blocks:
                        txt = " ".join(list(b.stripped_strings))
                        if len(txt) > best_len:
                            best_el, best_len = b, len(txt)
                    if best_el:
                        candidates.append(best_el)

                # Pick the first good candidate
                main = candidates[0] if candidates else soup

                # Convert to markdown-like plain text
                text_md = html2text.HTML2Text()
                text_md.ignore_links = True
                text_md.ignore_images = True
                text_md.body_width = 0
                text = text_md.handle(str(main))
                text = re.sub(r"\n{3,}", "\n\n", text).strip()

                # Final fallback if empty: use visible strings join
                if not text:
                    text = "\n\n".join(list(main.stripped_strings))[:8000]

                # Trim overly long content to keep prompt size under control
                MAX_LEN = 3000
                if len(text) > MAX_LEN:
                    text = text[:MAX_LEN]
                return {"url": u, "title": title, "text": text}
            except Exception:
                return None

        pages: List[Dict[str, str]] = []
        # Ensure max_workers is at least 1 to avoid ValueError when limited is empty
        worker_count = max(1, min(6, len(limited)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as ex:
            futures = [ex.submit(fetch, u) for u in limited]
            for f in concurrent.futures.as_completed(futures):
                item = f.result()
                if item:
                    # Reject obvious site-templates / not-found pages
                    text = item.get("text", "")
                    if not text or len(text) < 1000:
                        continue
                    if re.search(r"(pagina\s+die\s+u\s+zoekt\s+niet\s+vinden|page\s+not\s+found|404)", text, re.I):
                        continue
                    pages.append(item)
                    if len(pages) >= max_pages:
                        break
        return pages[:max_pages]

    def _retrieve_top_web_sources(
        self,
        question: str,
        chat_history: Optional[dict],
        target_count: int = 3,
    ) -> Tuple[str, List[str]]:
        """Simplified fast path: take top results and scrape first 3 with content."""
        try:
            search_query = self.generate_search_query(question=question, chat_history=chat_history)
        except Exception:
            search_query = (question or "").strip()

        # Wave 1: broad search (top 8)
        ddg_results: List[str] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(search_query, region="nl-nl", safesearch="moderate", max_results=8):
                    href = r.get("href")
                    if isinstance(href, str):
                        ddg_results.append(href)
        except Exception:
            pass

        # Normalize and prioritize authority NL domains, then other .nl
        candidates = self._postprocess_sources(ddg_results)
        def is_authority(u: str) -> bool:
            try:
                host = urlparse(u).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                return any(ah in host for ah in self.authority_hosts)
            except Exception:
                return False
        authority = [u for u in candidates if is_authority(u)]
        fallback_nl = [u for u in candidates if (u not in authority and self._is_nl_host(urlparse(u).netloc))]
        pool = authority + fallback_nl

        verified = self._verify_urls(pool)

        selected_pages: List[Dict[str, str]] = []
        idx = 0
        while len(selected_pages) < target_count and idx < len(verified):
            batch = verified[idx: idx + (target_count - len(selected_pages))]
            idx += len(batch)
            pages = self._fetch_and_parse_pages(batch, max_pages=len(batch))
            for p in pages:
                text = (p.get("text") or "").strip()
                host = urlparse(p.get("url", "")).netloc
                if len(text) >= 800 and (self._is_nl_host(host) or self._is_dutch_text(text)):
                    selected_pages.append(p)
                if len(selected_pages) >= target_count:
                    break

        block, urls = self._build_sources_block(selected_pages)
        return block, [p.get("url", "") for p in selected_pages]

    def _build_sources_block(self, pages: List[Dict[str, str]]) -> Tuple[str, List[str]]:
        """Create a structured sources block (no token budget) and return (block_text, candidate_urls).

        The block contains items as:
        <bron_1>
        URL: https://...
        Content:
        full page content
        </bron_1>
        """
        block_lines: List[str] = []
        candidate_urls: List[str] = []
        for idx, page in enumerate(pages, start=1):
            url = page.get("url", "")
            text = (page.get("text", "") or "").strip()
            # Ensure we don't have excessive blank lines: collapse 3+ newlines to 2
            text = re.sub(r"\n{3,}", "\n\n", text)
            # Use the already-truncated page content from the fetch step
            item = f"<bron_{idx}>\nURL: {url}\nContent:\n{text}\n</bron_{idx}>\n"
            block_lines.append(item)
            candidate_urls.append(url)
        return ("\n".join(block_lines) if block_lines else ""), candidate_urls
            
    def _retrieve_chunks_for_query(
        self, 
        vector_query: str, 
        user_message: str,
        year: List[int], 
        fiscal_topic: List[str]
    ) -> Tuple[List[Dict], Dict]:
        """
        Retrieve and prepare relevant chunks for a query if vector search is enabled.
        
        Args:
            vector_query: The concise, neutral query for vector search
            user_message: The original user message
            year: List of years the question relates to
            fiscal_topic: List of fiscal topics
            
        Returns:
            Tuple containing:
            - List of all raw chunks
            - Dictionary of formatted chunks
        """
        toggle_vector_search = Credentials.get_toggle_vector_search()
        all_raw_chunks, formatted_dict = [], {}
        
        # Only perform search if vector search is on and we have valid fiscal topics
        if toggle_vector_search == ToggleVectorSearch.ON.value and FiscalTopic.ONBEKEND.value not in fiscal_topic:
            # Retrieve relevant chunks based on the query
            logger.info(f"Retrieving chunks for vector query '{vector_query}' with fiscal topics: {fiscal_topic}")
            chunks = self._retrieve_and_prepare_chunks(vector_query, year, fiscal_topic)
            
            # If we have chunks, format them for the prompt
            if chunks:
                logger.info(f"Retrieved {len(chunks)} relevant chunks")
                formatted_dict = self._format_chunks_as_dict(user_message, chunks)
                all_raw_chunks = chunks
            else:
                logger.warning("No chunks found for the query")
        else:
            logger.info(f"Skipping vector search (toggle: {toggle_vector_search}, fiscal_topic: {fiscal_topic})")
            
        return all_raw_chunks, formatted_dict
    
    def _build_tax_query_prompt(
        self, 
        user_message: str, 
        tone_of_voice: str, 
        relevant_history: str,
        formatted_dict: Dict
    ) -> str:
        """
        Build the user prompt for tax query.
        
        Args:
            user_message: The original user message
            tone_of_voice: The desired tone for the response
            relevant_history: Extracted relevant chat history
            formatted_dict: Dictionary of formatted chunks
            
        Returns:
            Formatted user prompt
        """
        return user_prompt_templates.tax_query_user_prompt.format(
            chat_history=relevant_history,
            query=user_message,
            tone_of_voice=tone_of_voice,
            chunks_str=[formatted_dict]
        )
    
    def _prepare_final_response(
        self, 
        current_full_answer: str, 
        used_chunk_ids: Set[str],
        all_raw_chunks: List[Dict],
        additional_web_urls: Optional[List[str]] = None,
    ) -> Iterator[Union[str, dict]]:
        """
        Prepare and return the final response with used chunks.
        
        Args:
            current_full_answer: The full answer text
            used_chunk_ids: Set of used chunk IDs
            all_raw_chunks: List of all raw chunks
            
        Yields:
            The final response parts
        """
        # Prepare chunk data in advance (optimization)
        chunk_map = self._build_chunk_map(all_raw_chunks)

        # Fallback: ensure at least one source is used
        if not used_chunk_ids and all_raw_chunks:
            try:
                first_chunk_id = all_raw_chunks[0].get(n.ID)
                if first_chunk_id:
                    used_chunk_ids.add(first_chunk_id)
            except Exception:
                pass

        # Build the final response with used chunks
        logger.info(f"Creating synthetic response with {len(used_chunk_ids)} used chunks")
        synthetic_response = TaxQueryResponse(
            answer=current_full_answer,
            chunks=[ChunkInfo(chunk_id=cid, used=True) for cid in used_chunk_ids]
        )

        final_answer, filtered_urls, filtered_chunks = self._process_llm_response(
            synthetic_response, all_raw_chunks, additional_web_urls=additional_web_urls
        )

        # Return chunk data using chunk map for consistency
        try:
            filtered_chunk_ids = [chunk.chunk_id for chunk in filtered_chunks]
            used_chunks = []
            
            # Create a mapping from raw URLs to display text for easy lookup
            url_to_display_text = {}
            if filtered_urls:
                for filtered_url in filtered_urls:
                    # Parse markdown link format [display](url)
                    url_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', filtered_url)
                    if url_match:
                        display_text, url = url_match.groups()
                        url_to_display_text[url] = display_text
            
            # Use chunk map for each chunk's metadata
            for chunk_id in filtered_chunk_ids:
                chunk_data = chunk_map.get(chunk_id)
                if chunk_data:
                    # Replace title with enhanced display text if available
                    if chunk_data.get("source_url") in url_to_display_text:
                        chunk_data["title"] = url_to_display_text[chunk_data["source_url"]]
                    
                    used_chunks.append(chunk_data)
            
            # Filter out duplicate chunks based on title
            unique_chunks = self._filter_duplicate_chunks(used_chunks)
            
            # Send only filtered URLs to the frontend
            chunks_data = {"filtered_urls": filtered_urls}
            

            
            try:
                # Convert to JSON directly (avoid redundant validation)
                chunks_json = json.dumps(chunks_data)
                yield "\n###CHUNKS###" + chunks_json
            except Exception as e:
                logger.error(f"Error serializing chunks data: {e}")
                # Fall back to a simplified version
                yield "\n###CHUNKS###" + json.dumps({"used_chunks": []})

        except Exception as e:
            logger.error(f"Error adding chunks data to response: {e}")
            
    def _build_chunk_map(self, all_raw_chunks: List[Dict]) -> Dict[str, Dict]:
        """
        Build a map of chunk IDs to chunk data for faster lookup.
        
        Args:
            all_raw_chunks: List of all raw chunks
            
        Returns:
            Dictionary mapping chunk IDs to chunk data
        """
        chunk_map = {}
        
        for chunk in all_raw_chunks:
            chunk_id = chunk.get(n.ID) if isinstance(chunk, dict) else getattr(chunk, 'id', None)
            if chunk_id:
                # Pre-extract the needed fields to avoid nested lookups later
                metadata = chunk.get(n.METADATA, {})
                source_url = metadata.get(n.METADATA_SOURCE_URL, chunk.get("source_url", n.NOT_APPLICABLE))
                title = metadata.get(n.METADATA_TITLE)
                page_numbers = metadata.get("page_numbers")
                headers = metadata.get("headers")
                
                # Only include chunks that have a database title
                if source_url != n.NOT_APPLICABLE and title:
                    chunk_map[chunk_id] = {
                        "id": chunk_id,
                        "source_url": source_url,
                        "title": title,
                        "page_numbers": page_numbers,
                        "headers": headers
                    }
        
        return chunk_map
        
    def _filter_duplicate_chunks(self, used_chunks: List[Dict]) -> Dict[str, Dict]:
        """
        Filter out duplicate chunks based on title.
        
        Args:
            used_chunks: List of used chunks
            
        Returns:
            Dictionary mapping titles to unique chunks
        """
        unique_chunks = {}
        for chunk in used_chunks:
            # Use the title as the key for uniqueness
            title = chunk.get("title", "")
            if title and title not in unique_chunks:
                unique_chunks[title] = chunk
        return unique_chunks

    """
    Helper Methods
    """

    def _get_new_text_suffix_prefix(self, old_so_far: str, new_text: str) -> str:
        """
        Returns only the substring of `new_text` that
        extends beyond `old_so_far`.
        """
        if len(new_text) <= len(old_so_far):
            # Skip if new text is empty or repeated
            return ""
        # Otherwise, just yield the difference at the end:
        return new_text[len(old_so_far):]

    def _extract_relevant_chat_history(self, chat_history: list) -> dict:
        """
        Extracts up to three recent user-assistant message pairs and returns them as a dictionary.

        Args:
            chat_history (list): The list of chat messages.

        Returns:
            dict: A dictionary containing the recent chat pairs.
        """
        pairs = []
        current_user_msg = None

        # Go through the chat history in chronological order.
        for msg in chat_history:
            if msg["role"] == "user":
                current_user_msg = msg["message"]
            elif msg["role"] == "assistant" and current_user_msg is not None:
                pairs.append({"gebruiker": current_user_msg, "assistent": msg["message"]})
                current_user_msg = None

        # Take the last three pairs.
        last_pairs = pairs[-3:]

        return {"chat_history": last_pairs}

    def _retrieve_and_prepare_chunks(
        self,
        vector_query: str,
        year: List[int],
        fiscal_topic: List[str],
        initial_limit: int = 15,
    ) -> List[Dict]:
        """
        Retrieve context chunks based on the vector query and fiscal topics.
        
        Args:
            vector_query: The concise, neutral query for vector search
            year: List of years the query relates to
            fiscal_topic: List of fiscal topics from FiscalTopic enum (as string values)
            initial_limit: Maximum number of chunks to retrieve
            
        Returns:
            List of relevant document chunks
        """
        try:
            # Skip if the only fiscal topic is "Onbekend"
            if len(fiscal_topic) == 1 and fiscal_topic[0] == "Onbekend":
                logger.info("Not performing search since fiscal topic is 'Onbekend'")
                return []
                
            logger.info(f"Retrieving chunks for vector query: '{vector_query}' with years: {year} and fiscal topics: {fiscal_topic}")
            
            # Perform hybrid search
            t_start = datetime.now()
            context_chunks = self.vector_store.hybrid_search(
                query=vector_query,
                year=year,
                fiscal_topic=fiscal_topic,
                limit=initial_limit,
            )
            search_duration = (datetime.now() - t_start).total_seconds()
            
            # Log search duration and results
            if not context_chunks:
                logger.info(f"No chunks found for the query (search took {search_duration:.2f}s)")
                return []

            logger.info(f"Search completed in {search_duration:.2f}s, found {len(context_chunks)} chunks")

            # Return the chunks
            return context_chunks

        except Exception as e:
            logger.error(f"Error retrieving and preparing chunks: {e}", exc_info=True)
            return []

    def _process_llm_response(self, response: TaxQueryResponse, all_chunks: List[Dict], additional_web_urls: Optional[List[str]] = None) -> Tuple[str, List[str], List[ChunkInfo]]:
        """
        Process the language model's response to generate the final answer and return the used URLs.
        """
        try:
            # Create a mapping from raw chunk ID to the chunk dictionary.
            chunk_id_to_chunk = {chunk.get(n.ID): chunk for chunk in all_chunks}
            logger.info(f"Available chunk IDs in all_chunks: {list(chunk_id_to_chunk.keys())}")

            # Identify which chunks were used in the response (using dot notation on the Pydantic model).
            response_used_chunks = {chunk.chunk_id for chunk in response.chunks if chunk.used}
            logger.info(f"Chunks used in response: {response_used_chunks}")

            # Create ChunkInfo objects for used chunks from the raw chunks.
            used_chunks = [
                ChunkInfo(
                    chunk_id=chunk_id,
                    used=True
                )
                for chunk_id in response_used_chunks
                if chunk_id in chunk_id_to_chunk
            ]
            
            # Log which chunk IDs were not found
            missing_chunk_ids = [chunk_id for chunk_id in response_used_chunks if chunk_id not in chunk_id_to_chunk]
            if missing_chunk_ids:
                logger.warning(f"Chunk IDs not found in all_chunks: {missing_chunk_ids}")
            
            logger.info(f"Created {len(used_chunks)} ChunkInfo objects for used chunks")
            
            # Process all chunks (no filtering needed since all data is 'primaire')
            filtered_chunks = []
            filtered_urls: List[str] = []
            seen_urls: Set[str] = set()

            for chunk_info in used_chunks:
                chunk = chunk_id_to_chunk.get(chunk_info.chunk_id)
                if not chunk:
                    logger.warning(f"Chunk ID {chunk_info.chunk_id} not found in all_chunks.")
                    continue

                filtered_chunks.append(chunk_info)
                url = chunk.get(n.METADATA, {}).get(n.METADATA_SOURCE_URL, chunk.get("source_url", n.NOT_APPLICABLE))
                
                if chunk_info.used and url != n.NOT_APPLICABLE and url not in seen_urls:
                    seen_urls.add(url)
                    
                    display_label = chunk.get(n.METADATA_TITLE)
                    
                    # Check if URL contains BWBR (Wetten Overheid)
                    if "BWBR" in url:
                        # For Wetten Overheid URLs, use title and append headers if available
                        headers = chunk.get("headers")
                        if headers and isinstance(headers, list) and len(headers) > 0:
                            # Sanitize headers to extract short identifiers from long descriptions
                            sanitized_headers = self.sanitize_headers(headers)
                            if len(sanitized_headers) == 1:
                                display_label += f" - {sanitized_headers[0]}"
                            else:
                                display_label += f" - {', '.join(sanitized_headers)}"
                    
                    # Append page numbers if available (for PDFs)
                    page_numbers = chunk.get("page_numbers")
                    if page_numbers and isinstance(page_numbers, list) and len(page_numbers) > 0:
                        if len(page_numbers) == 1:
                            display_label += f" - pagina {page_numbers[0]}"
                        else:
                            display_label += f" - pagina's {', '.join(map(str, page_numbers))}"

                    # Create markdown link with display label
                    formatted_url = f"[{display_label}]({url})"
                    filtered_urls.append(formatted_url)
                    logger.info(f"Added URL: {display_label} ({url})")

            # Also handle any used chunk_ids that are direct web URLs (from <web_sources>)
            for cid in response_used_chunks:
                if isinstance(cid, str) and (cid.startswith("http://") or cid.startswith("https://")):
                    if cid not in seen_urls:
                        seen_urls.add(cid)
                        # Build label: Domain – LastPathSegment
                        try:
                            parsed = urlparse(cid)
                            host = parsed.netloc.replace("www.", "")
                            path_part = unquote(parsed.path.strip("/"))
                            last_seg = path_part.split("/")[-1] if path_part else ""
                            def prettify(text: str) -> str:
                                t = re.sub(r"[-_]+", " ", text)
                                return re.sub(r"\s+", " ", t).strip().title()
                            site_label = prettify(host.split(":")[0].split(".")[-2] if "." in host else host)
                            topic_label = prettify(last_seg) if last_seg else host
                            label = f"{site_label} – {topic_label}"
                        except Exception:
                            label = "Bron"
                        filtered_urls.append(f"[{label}]({cid})")

            # If web augmentation ran and model returned no web URLs, add top-1 to ensure at least one
            if additional_web_urls and len(additional_web_urls) > 0:
                try:
                    # Add first verified URL if not already present
                    first_url = additional_web_urls[0]
                    if first_url not in seen_urls:
                        seen_urls.add(first_url)
                        parsed = urlparse(first_url)
                        host = parsed.netloc.replace("www.", "")
                        path_part = unquote(parsed.path.strip("/"))
                        last_seg = path_part.split("/")[-1] if path_part else ""
                        label = (host.split(".")[-2] if "." in host else host).title()
                        if last_seg:
                            label = f"{label} – {re.sub(r'[-_]+', ' ', last_seg).title()}"
                        filtered_urls.append(f"[{label}]({first_url})")
                except Exception:
                    pass

            # Log final selection
            logger.info(f"Final selection: {len(filtered_chunks)} chunks and {len(filtered_urls)} URLs")

            # Use attribute access for the response's answer.
            final_response = response.answer.strip()
            return final_response, filtered_urls, filtered_chunks

        except Exception as e:
            logger.error(f"Error processing LLM response: {e}")
            return "Er is een fout opgetreden bij het verwerken van de reactie.", [], []

    def _format_chunks_as_dict(self, query: str, chunks: List[Dict]) -> dict:
        """
        Format the list of chunks into a structured dictionary for a given query.

        Args:
            query (str): The query or subquestion.
            chunks (List[Dict]): A list of raw chunk dictionaries.

        Returns:
            dict: A dictionary with the question and its associated chunks.
        """
        formatted_chunks = []
        for chunk in chunks:            
            metadata = chunk.get(n.METADATA, {})
            formatted_chunks.append({
                "source_id": chunk.get(n.ID),
                "year": metadata.get(n.METADATA_YEAR),
                "category": metadata.get(n.METADATA_DATA_CATEGORY),
                "source": metadata.get(n.METADATA_SOURCE),
                "title": metadata.get(n.METADATA_TITLE),
                "content": chunk.get(n.CONTENT).strip()
            })
        return {"sources": formatted_chunks}

    def clean_vector_query(self, vector_query: str) -> str:
        """
        Remove years (4-digit numbers) from the vector query to make the search more generic.
        
        This method uses regex to identify and remove years while preserving the rest of the query.
        It handles various year formats and ensures the query remains meaningful after year removal.
        
        Args:
            vector_query (str): The original vector query that may contain years.
            
        Returns:
            str: The cleaned vector query with years removed.
        """
        if not vector_query or not isinstance(vector_query, str):
            return vector_query
            
        # Regex pattern to match 4-digit years (1900-2099)
        year_pattern = r'\b(19|20)\d{2}\b'
        
        # Remove years from the query
        cleaned_query = re.sub(year_pattern, '', vector_query)
        
        # Clean up extra whitespace that might be left after removing years
        # Replace multiple spaces with single space and strip leading/trailing whitespace
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # Remove common artifacts that might be left after year removal
        # Remove "voor" or "in" that might be left hanging
        cleaned_query = re.sub(r'\b(voor|in)\s+$', '', cleaned_query)
        cleaned_query = re.sub(r'^\s+(voor|in)\s+', '', cleaned_query)
        
        # Final cleanup of any remaining extra whitespace
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        logger.info(f"Cleaned vector query: '{vector_query}' -> '{cleaned_query}'")
        
        return cleaned_query

    def sanitize_headers(self, headers: List[str]) -> List[str]:
        """
        Sanitize headers by extracting short identifiers from long descriptive text.
        
        This method looks for patterns like "10.2. vrees voor verduistering..." and extracts
        just the short identifier "10.2." or "Artikel 47a." from longer descriptions.
        
        Args:
            headers (List[str]): List of header strings to sanitize.
            
        Returns:
            List[str]: List of sanitized headers.
        """
        if not headers or not isinstance(headers, list):
            return headers
            
        sanitized_headers = []
        
        for header in headers:
            if not header or not isinstance(header, str):
                sanitized_headers.append(header)
                continue
                
            # Look for patterns like "10.2. " or "Artikel 47a. " (period followed by space)
            # This indicates a short identifier followed by descriptive text
            match = re.search(r'^(.+?\.)\s+', header)
            
            if match:
                # Extract just the identifier part (e.g., "10.2." or "Artikel 47a.")
                identifier = match.group(1)
                sanitized_headers.append(identifier)
            else:
                # If no pattern found, keep the original header unchanged
                sanitized_headers.append(header)
        
        return sanitized_headers
