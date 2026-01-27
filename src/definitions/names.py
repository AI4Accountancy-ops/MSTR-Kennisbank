# Credentials
AZURE_OPENAI_API_KEY = "openai-api-key"
AZURE_OPENAI_ENDPOINT = "openai-endpoint"
AZURE_OPENAI_MODEL_NAME = "openai-model"
ANTHROPIC_API_KEY = "anthropic-api-key"
GEMINI_API_KEY = "gemini-api-key"
LLAMA_API_KEY = "llama-api-key"
AZURE_STORAGE_ACCOUNT_NAME = "storage-account-name"
AZURE_STORAGE_CONNECTION_STRING = "storage-connection-string"
AZURE_STORAGE_CONTAINER_NAME = "storage-container-name"
PGVECTOR_CNX = "postgresql-connection-string"
COHERE_API_KEY = "cohere-api-key"
GOOGLE_CREDENTIALS_JSON = "google-credentials-json"
OPENAI_ASSISTANTS_API_KEY = "openai-assistants-api-key"
PERPLEXITY_API_KEY = "perplexity-api-key"
CONTAINER_REGISTRY_PASSWORD = "container-registry-password"
SLACK_TOKEN = "slack-token"
SCRAPING_CREDENTIALS = "scraping-credentials"
EMBEDDING_LINK = "embedding-link"
COSMOS_CONNECTION_STRING = "cosmos-connection-string"
COSMOS_ENDPOINT = "cosmos-endpoint"
COSMOS_API_KEY = "cosmos-api-key"

# Cosmos
COSMOS_API_KEY = "cosmos-api-key"
COSMOS_CONNECTION_STRING = "cosmos-connection-string"
COSMOS_DATABASE_NAME = "configs"
COSMOS_ENDPOINT = "cosmos-endpoint"
COSMOS_FEEDBACK_METADATA_CONTAINER_NAME = "feedback_chat"
COSMOS_CHAT_HISTORY_CONTAINER_NAME = "chat_history"
COSMOS_WHITELIST_CONTAINER_NAME = "whitelist"

# Stripe Credentials
STRIPE_API_KEY = "stripe-api-key"
STRIPE_PRODUCT_ID = "stripe-product-id"
STRIPE_WEBHOOK_SECRET = "stripe-webhook-secret"
SUBSCRIPTION_SYNC_TOKEN = "subscription-sync-token"

# Scraping Credentials
NEXTENS_USERNAME = "nextens-username"
NEXTENS_PASSWORD = "nextens-password"
MFAS_USERNAME = "mfas-username"
MFAS_PASSWORD = "mfas-password"
INDICATOR_USERNAME = "indicator-username"
INDICATOR_PASSWORD = "indicator-password"



# Scraper element identifiers
BTW = "BTW"
IB = "IB"
VPB = "VPB"
OMZETBELASTING = "Omzetbelasting"
INKOMSTENBELASTING = "Inkomstenbelasting"
VENNOOTSCHAPSBELASTING = "Vennootschapsbelasting"
BROCHURE_BTW = "Btw"

# Assistant Keywords
ACCOUNTING_ASSISTANT = "Rekenassistent"
TYPE = "type"
CODE_INTERPRETER = "code_interpreter"
ASSISTANTS = "assistants"
QUERY_FILE = "query_file"
UPLOADED_FILE = "uploaded_file"
STATUS = "status"
PROCESSED = "processed"
FILE_IDS = "file_ids"
USER = "user"

# Nextens Metadata
NEXTENS_INPUT_FOLDER = "extracted_nextens"
NEXTENS_SOURCE_TYPE = "nextens"
NEXTENS_YEAR = "2024"
NEXTENS_TAX_TYPE = "omzetbelasting"

# MFAS Metadata
MFAS_INPUT_FOLDER = "extracted_mfas"

# Utils
AUTHENTICATED = "authenticated"
LATEST_METADATA = "latest_metadata"
CHAT_HISTORY = "chat_history"
CURRENT_PAGE = "current_page"

# LLM factory
MODEL = "model"
TEMPERATURE = "temperature"
MAX_RETRIES = "max_retries"
MAX_TOKENS = "max_tokens"
RESPONSE_MODEL = "response_model"
MESSAGES = "messages"
OPENAI = "openai"
AZURE_OPENAI = "azure_openai"
ANTHROPIC = "anthropic"
LLAMA = "llama"
STREAM = "stream"

# .txt Markers
TXT_SOURCE_URL = "Source URL: "

# Metadata
METADATA_YEAR = "year"
METADATA_DATA_CATEGORY = "data_category"
METADATA_FISCAL_TOPIC = "fiscal_topic"
METADATA_TARGET_GROUP = "target_group"
METADATA_TITLE = "title"
METADATA_INFORMATION_TYPE = "information_type"
METADATA_SOURCE = "source"
METADATA_SOURCE_URL = "source_url"

# Search dictionary
ID = "id"
DOCUMENT_CHUNKS = "document_chunks"
VECTOR = "vector"
CONTENT = "content"
METADATA = "metadata"
KEYWORD = "keyword"
KEYWORD_SCORE = "keyword_score"
SIMILARITY_SCORE = "similarity_score"
SEMANTIC = "semantic"
SEMANTIC_SCORE = "semantic_score"
RERANK_SCORE = "rerank_score"
RERANK = "rerank"
FINAL_SCORE = "final_score"
RELEVANCE_SCORE = "relevance_score"

# Email keywords
NOT_APPLICABLE = "N/A"
UNTITLED = "Untitled"
PAYLOAD = "payload"
PARTS = "parts"
ME = "me"
BODY = "body"
ATTACHMENT_ID = "attachmentId"
UNREAD = "UNREAD"
DATA = "data"
GMAIL = "gmail"
V1 = "v1"
NAME = "name"
LABELS = "labels"

# Response model keywords
SYNTHESIZED_QA_PAIRS = "synthesized_qa_pairs"
QA_PAIR_ID = "qa_pair_id"
SUBJECT = "subject"
CONTEXT = "context"
DATE_NOW = "date_now"
DATE_RECEIVED = "date_received"
SENDER = "sender"
QUESTION = "question"
SYNTHESIZED_ANSWER = "synthesized_answer"
CHUNKS = "chunks"
SOURCES = "sources"
ONBEKEND = "onbekend"

# File extensions
PDF = ".pdf"
DOCX = ".docx"

# Azure postgres
POSTGRES_HOST = "POSTGRES-HOST"
POSTGRES_DB = "POSTGRES-DB"
POSTGRES_USER = "POSTGRES-USER"
POSTGRES_PASSWORD = "POSTGRES-PASSWORD"
POSTGRES_PORT = "POSTGRES-PORT"

# Prefix
SUBVRAAG = "Subvraag - "

# Spinner flags
ANALYSIS_STARTED_FLAG = "__ANALYSIS_STARTED__"
ANALYSIS_FINISHED_FLAG = "__ANALYSIS_FINISHED__"
DOCS_RETRIEVED_FLAG = "__DOCS_RETRIEVED_FLAG__"
DOCS_RETRIEVED = "docs_retrieved"
RETRIEVAL_STARTED_FLAG = "__RETRIEVAL_STARTED__"
RETRIEVAL_STARTED = "retrieval_started"
WEB_VERIFYING_FLAG = "__WEB_VERIFYING__"
WEB_VERIFYING = "web_verifying"
ANALYZING_SOURCES_FLAG = "__ANALYZING_SOURCES__"
RETRIEVING_MORE_SOURCES_FLAG = "__RETRIEVING_MORE_SOURCES__"
FLAG = "flag"
ERROR = "error"
MESSAGE = "message"

# Session State
ALL_RAW_CHUNKS = "all_raw_chunks"

# API Keywords
REASONING_EFFORT = "reasoning_effort"
TONE_OF_VOICE = "tone_of_voice"
NORMAAL = "Normaal"
PENDING_QUESTION = "pending_question"
DEEP_RESEARCH = "deep_research"

# Admin Settings
ADMIN_PASSWORD = "admin-password"
CONFIG_AUTHENTICATED = "config_authenticated"
ACTIVE_SYSTEM_PROMPT = "active_system_prompt"
SYSTEM_PROMPTS = "system_prompts"
LOADED_PROMPTS = "loaded_prompts"
EDIT_PROMPT_ID = "edit_prompt_id"
EDIT_PROMPT_NAME = "edit_prompt_name"
EDIT_PROMPT_CONTENT = "edit_prompt_content"
ACTIVE = "active"
PROMPT_ID = "id"
PROMPT_NAME = "prompt_name"

# Toggle Vector Search
TOGGLE_VECTOR_SEARCH = "toggle-vector-search"

# M365 Connector Credentials
CONNECTOR_MICROSOFT_CLIENT_ID = "connector-microsoft-client-id"
CONNECTOR_MICROSOFT_CLIENT_SECRET = "connector-microsoft-client-secret"
CONNECTOR_MICROSOFT_TENANT_ID = "connector-microsoft-tenant-id"
CONNECTOR_MICROSOFT_REDIRECT_URI = "connector-microsoft-redirect-uri"
CONNECTOR_MICROSOFT_CLIENT_STATE_SECRET = "connector-microsoft-client-state-secret"
CONNECTOR_MICROSOFT_WEBHOOK_URL = "connector-microsoft-webhook-url"