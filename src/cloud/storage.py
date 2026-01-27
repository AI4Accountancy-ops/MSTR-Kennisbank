import json
import os
import tempfile
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

import utils.input_output as io
from definitions.credentials import Credentials
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class AzureStorageClient:
    def __init__(self, account_name: str = None, container_name: str = None):
        self.account_name = Credentials.get_azure_storage_account_name()
        self.container_name = Credentials.get_azure_storage_container_name()
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.account_name}.blob.core.windows.net",
            credential=credential,
        )
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

    def upload_blob(self, blob_name: str, file_path: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info(f"Uploaded {blob_name} to container {self.container_name}.")

    def upload_folder(self, folder_path: str):
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                self.upload_blob(file_path, file_path)
        logger.info(f"Uploaded {folder_path} to container {self.container_name}.")

    def upload_text_as_blob(self, blob_name: str, text_data: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(text_data, blob_type="BlockBlob", overwrite=True)
        logger.info(
            f"Saved text data to {blob_name} in container {self.container_name}."
        )

    def upload_json_as_blob(self, blob_name: str, json_data: dict):
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            json.dumps(json_data), blob_type="BlockBlob", overwrite=True
        )
        logger.info(
            f"Saved json data to {blob_name} in container {self.container_name}."
        )

    def download_blob(self, blob_name: str, download_file_path: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        with open(download_file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        logger.info(f"Downloaded {blob_name} to {download_file_path}.")

    def download_blob_to_memory(self, blob_name: str) -> Any:
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()

        # Determine the file extension
        _, file_extension = os.path.splitext(blob_name)

        blob_data = self._decode_file(
            blob_data=blob_data, blob_name=blob_name, file_extension=file_extension
        )
        return blob_data

    def list_blobs(self, folder: str = "") -> list[str]:
        return [
            blob.name
            for blob in self.container_client.list_blobs()
            if folder in blob.name
        ]

    def list_blobs_in_folder(self, folder_path: str) -> list[str]:
        if not folder_path.endswith("/"):
            folder_path += "/"

        blob_list = [
            blob.name
            for blob in self.container_client.list_blobs(name_starts_with=folder_path)
        ]
        return blob_list

    def remove_blob(self, blob_name: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        logger.info(f"Removed {blob_name} from container {self.container_name}.")

    def remove_folder(self, folder_path: str):
        if not folder_path.endswith("/"):
            folder_path += "/"
        blobs = self.list_blobs_in_folder(folder_path)
        for blob in blobs:
            self.remove_blob(blob)

    def folder_exists(self, folder_path: str) -> bool:
        folder_exists = False

        # Ensure the folder path ends with a slash
        if not folder_path.endswith("/"):
            folder_path += "/"

        # Check if any blobs exist with the given prefix
        blobs = list(self.container_client.list_blobs(name_starts_with=folder_path))
        if blobs:
            folder_exists = True
        return folder_exists

    def blob_exist(self, blob_name: str) -> bool:
        blob_client = self.container_client.get_blob_client(blob_name)
        exists = blob_client.exists()
        return exists

    """
    Helpers
    """

    def _decode_file(self, blob_data: Any, blob_name: str, file_extension: str) -> Any:
        if file_extension.lower() == ".txt":
            # Decode as plain text
            try:
                return blob_data.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(f"Could not decode {blob_name} as text.")
        elif file_extension.lower() == ".pdf":
            # Handle PDF file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(blob_data)
                return io.read_pdf_as_text(temp_file.name)
        elif file_extension.lower() == ".docx":
            # For .docx, return the binary data as is
            return blob_data
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
