import time
from typing import Any, Dict, List, Optional

import requests
from openai import AzureOpenAI

import definitions.names as n
from logger.logger import Logger
from config.settings import get_settings

logger = Logger.get_logger(__name__)


class AssistantsFactory:
    """
    A factory class for creating and managing assistants with Azure OpenAI.
    """

    def __init__(self):
        self.settings = get_settings().azure_openai
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        """
        Initialize the Azure OpenAI client.
        """
        return AzureOpenAI(
            api_key=self.settings.api_key,
            api_version=self.settings.api_version,
            azure_endpoint=self.settings.api_base,
        )

    def create_assistant(
        self,
        instructions: str,
        tools: Optional[List[Dict]] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Create an assistant with optional tools and resources.

        Args:
            instructions (str): Instructions for the assistant.
            tools (Optional[List[Dict]]): Tools for the assistant.
            tool_resources (Optional[Dict[str, Any]]): Additional resources for tools.
            model (Optional[str]): Model to use (defaults to the factory's default model).

        Returns:
            str: The ID of the created assistant.
        """
        model_to_use = model or self.settings.default_model

        assistant = self.client.beta.assistants.create(
            instructions=instructions,
            model=model_to_use,
            tools=tools or [],
            tool_resources=tool_resources or {},
        )
        logger.info(f"Assistant created with ID: {assistant.id}")
        return assistant.id

    def upload_file(
        self, file_data: bytes, purpose: str = n.ASSISTANTS, filename: str = n.UPLOADED_FILE
    ) -> Dict[str, Any]:
        """
        Upload a file to Azure OpenAI.

        Args:
            file_data (bytes): The file data in bytes.
            purpose (str): The purpose of the upload (e.g., 'assistants').
            filename (str): The name of the uploaded file.

        Returns:
            Dict[str, Any]: The response data from the Azure OpenAI API.
        """
        url = f"{self.settings.api_base}openai/files?api-version={self.settings.api_version}"
        headers = {"api-key": self.settings.api_key}
        files = {
            "file": (filename, file_data, "application/octet-stream"),
            "purpose": (None, purpose),
        }

        response = requests.post(url, headers=headers, files=files)
        response_data = response.json()

        if response.status_code in [200, 201] and response_data.get("status") == "processed":
            logger.info(f"File uploaded successfully: {response_data}")
            return response_data

        logger.error(f"File upload failed: {response.status_code}, {response.text}")
        raise ValueError(
            f"File upload failed. Status: {response.status_code}, Response: {response.text}"
        )

    def get_full_response(
            self,
            assistant_id: str,
            user_message: str,
            file_id: Optional[str] = None
    ) -> str:
        """
        Send a message to the assistant (optionally with an uploaded file)
        and retrieve the full response at once.
        """
        # Create the initial user message for the thread
        message = {"role": n.USER, "content": user_message}
        if file_id:
            message["attachments"] = [{"file_id": file_id, "tools": [{n.TYPE: n.CODE_INTERPRETER}]}]

        # 1. Create a new thread with the user's message
        thread = self.client.beta.threads.create(messages=[message])
        thread_id = thread.id

        # 2. Start a run for that thread with the given assistant
        run = self.client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        run_id = run.id

        # 3. Poll the run until completed
        max_wait_time = 120  # seconds
        start_time = time.time()

        while True:
            run_status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run_status.status in ["completed", "failed", "cancelled", "expired"]:
                break
            elif run_status.status == "requires_action":
                # Handle the required action here if needed, otherwise raise the action.
                raise RuntimeError("Run requires action before continuing.")
            elif time.time() - start_time > max_wait_time:
                raise TimeoutError("Run timed out.")
            time.sleep(1)

        if run_status.status != "completed":
            raise RuntimeError(f"Run ended with status: {run_status.status}")

        # 4. Once completed, retrieve the thread messages
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        full_response_segments = []
        for msg in messages.data:
            if msg.role == "assistant":
                for segment in msg.content:
                    if segment.type == "text":
                        full_response_segments.append(segment.text.value)

        full_response = "\n".join(full_response_segments).strip()

        if full_response:
            return full_response

        raise RuntimeError("No assistant message found after run completion.")
