import { API_BASE_URL } from '~/config/environment';
import { FeedbackRequest, MessageFeedbackRequest } from './types';

export const saveFeedback = async (feedback: FeedbackRequest) => {
  const response = await fetch(`${API_BASE_URL}/save_feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(feedback),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const messageFeedback = async (messageFeedback: MessageFeedbackRequest) => {
  const response = await fetch(`${API_BASE_URL}/message_feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(messageFeedback),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};