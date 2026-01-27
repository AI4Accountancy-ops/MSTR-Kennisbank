from slack_sdk import WebClient

from src.definitions.credentials import Credentials


class SlackClient:
    def __init__(self):
        self.client = WebClient(Credentials.get_slack_token())
        self.channel_id = 'errors-applications'

    def send_message(self, message: str):
        # Send a message to the channel
        response = self.client.chat_postMessage(
            channel=self.channel_id,
            text=message
        )
        return response
