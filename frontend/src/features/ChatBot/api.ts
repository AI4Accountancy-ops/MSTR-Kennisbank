import { API_BASE_URL } from '~/config/environment';

export interface ChatRequest {
  user_message: string;
  tone_of_voice: string;
  chat_history: unknown[];
  user_id: string;
  web_search?: boolean;
}

/**
 * Sends a chat message to the API and processes the streaming response
 * @param data Request data containing user message and chat history
 * @param onStreamUpdate Callback function to handle streaming updates
 */
export const sendChatMessage = async (
  data: ChatRequest,
  onStreamUpdate: (chunk: string) => void,
): Promise<void> => {
  const response: Response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  let botMessage = '';
  const reader = response.body?.getReader();
  const decoder = new TextDecoder('utf-8');

  if (!reader) return;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      if (!botMessage.includes('\n###COMPLETE###')) {
        botMessage += '\n###COMPLETE###';
        onStreamUpdate(botMessage);
      }
      break;
    }

    const chunk = decoder.decode(value, { stream: true });

    if (chunk.includes('\n###CHUNKS###')) {
      const CHUNKS_MARKER = '\n###CHUNKS###';

      if (!botMessage.includes(CHUNKS_MARKER)) {
        const [beforeMarker, afterRaw = ''] = chunk.split(CHUNKS_MARKER);
        const afterMarker = afterRaw.trim().startsWith('{') ? afterRaw : '';

        botMessage += beforeMarker + CHUNKS_MARKER + afterMarker;
      } else {
        botMessage += chunk;
      }
    } else {
      botMessage += chunk;
    }

    onStreamUpdate(botMessage);
  }
};
