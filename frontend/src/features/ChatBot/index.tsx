import React, { useState, useEffect, useRef, FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
// MUI removed in PR6 for this file; using Tailwind/Shadcn classes instead

import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import { sendChatMessage } from './api';

import { useChatHistory } from '@features/ChatHistory/context/ChatHistoryContext';
import { getChatById, saveChatHistory } from '@features/ChatHistory/api';
import { getUserId } from '@features/Authentication/utils';

import type { Message, ProcessingStage } from './types';
import type { ChatMessage as FeedbackChatMessage } from '@features/Feedback/types';
import type { ChunkModal } from '@features/ChunksModal';

declare global {
  interface WindowEventMap {
    titleUpdated: CustomEvent<{
      chatId: string;
      newTitle: string;
      timestamp: number;
    }>;
  }
}

// Helper function to parse filtered_urls from markdown links
const markdownLinkRE = /\[([^\]]+)\]\(([^)]+)\)/;

function parseFilteredUrls(arr: string[]): ChunkModal[] {
  return arr.map((link, i) => {
    const [, label, url] = markdownLinkRE.exec(link) || [];
    return {
      id: `link_${i}`,
      title: label || `Bron ${i + 1}`,
      source_url: url || '',
    };
  });
}

const ChatBot: React.FC = () => {
  const { chatId } = useParams<{ chatId?: string }>();
  const { refetchHistory, history } = useChatHistory();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const [toneOfVoice, setToneOfVoice] = useState<string>('Normaal');
  const [processingStage, setProcessingStage] = useState<ProcessingStage>('analyzing');
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [scrollTimeout, setScrollTimeout] = useState<NodeJS.Timeout | null>(null);
  const [processingTimeMs, setProcessingTimeMs] = useState<number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState<boolean>(false);
  const [inputPosition, setInputPosition] = useState<'center' | 'bottom'>('center');
  const queryClient = useQueryClient();
  const spinnerTimeoutsRef = useRef<NodeJS.Timeout[]>([]);
  const retrievalStartedRef = useRef<boolean>(false);

  // Add a ref to track the last saved message
  const lastSavedMessageRef = useRef<string>('');

  // Add a ref to track the most recently edited title to handle race conditions
  const lastEditedTitleRef = useRef<string>('');

  // Listen for title updates to track the most recent edit
  useEffect(() => {
    const handleTitleUpdate = (event: CustomEvent) => {
      if (event.detail?.chatId === chatId && event.detail?.newTitle) {
        lastEditedTitleRef.current = event.detail.newTitle;
        console.log('[ChatBot] Tracked title update:', event.detail.newTitle);
      }
    };

    window.addEventListener('titleUpdated', handleTitleUpdate as EventListener);
    return () => {
      window.removeEventListener('titleUpdated', handleTitleUpdate as EventListener);
    };
  }, [chatId]);

  // Clear tracked title when chatId changes
  useEffect(() => {
    lastEditedTitleRef.current = '';
    console.log('[ChatBot] Cleared tracked title for new chat:', chatId);
  }, [chatId]);

  // Helper function to format chunks for modal
  const formatChunksForModal = (chunks: ChunkModal[]) => {
    return chunks.map(chunk => ({
      id: chunk.id || String(Math.random()),
      source_url: chunk.source_url || '',
      title: chunk.title || '',
    }));
  };

  // Fetch chat data if chatId is provided
  const { data: chat } = useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }
      return getChatById(chatId, getUserId());
    },
    enabled: !!chatId,
  });

  // Clear messages when there's no chatId (new chat)
  useEffect(() => {
    if (!chatId) {
      setMessages([]);
    }
  }, [chatId]);

  // Initialize messages from chat data when it's loaded
  useEffect(() => {
    if (chat && chat.chat && chat.chat.messages) {
      // Convert ChatPair[] to Message[]
      const convertedMessages: Message[] = chat.chat.messages.flatMap(pair => {
        const messages: Message[] = [];

        if (pair.user) {
          messages.push({
            sender: 'user',
            text: pair.user,
          });
        }

        if (pair.assistant) {
          messages.push({
            sender: 'bot',
            text: pair.assistant,
            usedChunks: pair.chunks
              ? pair.chunks.map(chunk => {
                  // Extract chunk data safely whether it's a string or an object
                  let chunkContent = '';
                  let chunkSource: string[] = [];
                  let chunkYear = 0;
                  let chunkSourceUrl = '';
                  let chunkId = String(Math.random());
                  let chunkTitle = '';

                  // Handle different chunk formats
                  if (typeof chunk === 'string') {
                    chunkContent = chunk;
                  } else if (typeof chunk === 'object' && chunk !== null) {
                    // If it's already a structured chunk object, extract its properties safely
                    const objChunk = chunk as Record<string, unknown>;
                    chunkContent =
                      typeof objChunk.content === 'string'
                        ? objChunk.content
                        : typeof objChunk.data_category === 'string'
                          ? objChunk.data_category
                          : '';

                    chunkSource = Array.isArray(objChunk.source) ? objChunk.source : [];
                    chunkYear = typeof objChunk.year === 'number' ? objChunk.year : 0;
                    chunkSourceUrl =
                      typeof objChunk.source_url === 'string' ? objChunk.source_url : '';
                    chunkTitle = typeof objChunk.title === 'string' ? objChunk.title : '';
                    if (typeof objChunk.id === 'string') {
                      chunkId = objChunk.id;
                    }
                  }

                  return {
                    id: chunkId,
                    content: chunkContent,
                    source: chunkSource,
                    year: chunkYear,
                    source_url: chunkSourceUrl,
                    title: chunkTitle,
                  };
                })
              : [],
            isBackendComplete: true, // <-- add this line to persist the flag
          });
        }

        return messages;
      });

      setMessages(convertedMessages);
    } else if (!chatId) {
      // If there's no chatId, ensure messages are empty for a new chat
      setMessages([]);
    }
  }, [chat, chatId]);

  // Save chat mutation
  const saveChatMutation = useMutation({
    mutationFn: async (chatData: {
      user_id: string;
      chat_title: string;
      chat_history: FeedbackChatMessage[];
      chat_id?: string;
    }) => {
      return saveChatHistory(chatData);
    },
    onSuccess: (newChatId: string | null) => {
      // Clear the tracked title after successful save
      lastEditedTitleRef.current = '';
      console.log('[ChatBot] Cleared tracked title after successful save');

      // Invalidate the chat query to refetch the updated data
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: ['chat', chatId] });
      } else if (newChatId) {
        // If this was a new chat, update the URL with the new chat ID
        navigate(`/chatbot/${newChatId}`, { replace: true });
        // Invalidate the chat query for the new chat ID
        queryClient.invalidateQueries({ queryKey: ['chat', newChatId] });
      }

      refetchHistory();
    },
  });

  // Helper function to save chat only if it's different from the last saved message
  const saveChatIfChanged = (updatedMessages: Message[]) => {
    // Create a string representation of the last bot message for comparison
    const lastBotMessage = updatedMessages
      .slice()
      .reverse()
      .find((msg: Message) => msg.sender === 'bot');
    if (!lastBotMessage) return;

    const messageSignature = `${lastBotMessage.text}-${lastBotMessage.isBackendComplete}`;

    // Only save if this is a different message than what we last saved
    if (messageSignature !== lastSavedMessageRef.current) {
      console.log('[ChatBot] Saving chat to backend - message changed');
      console.log('[ChatBot] Current chatId:', chatId);
      console.log('[ChatBot] Tracked title:', lastEditedTitleRef.current);
      lastSavedMessageRef.current = messageSignature;

      // For new chats, use the first user message as the title
      // For existing chats, preserve the current title to avoid overwriting user edits
      const getChatTitle = () => {
        if (chatId) {
          // First, check if we have a recently edited title for this chat
          if (lastEditedTitleRef.current && lastEditedTitleRef.current.trim() !== '') {
            console.log('[ChatBot] Using tracked title:', lastEditedTitleRef.current);
            return lastEditedTitleRef.current;
          }

          // Get the most up-to-date title from chat history context
          const allChats = [
            ...history.today,
            ...history.yesterday,
            ...history.previous_7_days,
            ...history.older,
          ];

          const existingChat = allChats.find(chat => chat.id === chatId);
          if (existingChat) {
            const currentTitle = existingChat.title;
            // Only use existing title if it's not a default value
            if (
              currentTitle &&
              currentTitle !== 'New Chat' &&
              currentTitle !== 'Nieuwe Chat' &&
              currentTitle.trim() !== ''
            ) {
              console.log('[ChatBot] Using history title:', currentTitle);
              return currentTitle;
            }
          }

          // If no proper title exists, generate one from the first user message
          const firstUserMessage = updatedMessages.find(msg => msg.sender === 'user');
          if (firstUserMessage) {
            const generatedTitle =
              firstUserMessage.text.substring(0, 30) +
              (firstUserMessage.text.length > 30 ? '...' : '');
            console.log('[ChatBot] Using generated title:', generatedTitle);
            return generatedTitle;
          }
          return 'New Chat';
        }
        // Find the first user message for new chats
        const firstUserMessage = updatedMessages.find(msg => msg.sender === 'user');
        if (!firstUserMessage) return 'New Chat';

        // Truncate the message to 30 characters with ellipsis if longer
        return (
          firstUserMessage.text.substring(0, 30) + (firstUserMessage.text.length > 30 ? '...' : '')
        );
      };

      const finalTitle = getChatTitle();
      console.log('[ChatBot] Final title to save:', finalTitle);

      // Save chat regardless of whether we have a chatId or not
      saveChatMutation.mutate({
        user_id: getUserId(),
        chat_title: finalTitle,
        chat_history: convertToChatHistory(updatedMessages),
        chat_id: chatId, // This will be undefined for new chats
      });
    } else {
      console.log('[ChatBot] Skipping save - message unchanged');
    }
  };

  // Update input position when messages change
  useEffect(() => {
    if (messages.length === 0) {
      setInputPosition('center');
    } else {
      setInputPosition('bottom');
    }
  }, [messages.length]);

  // Improved scroll behavior with enhanced smoothness
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end',
        inline: 'nearest',
      });
    }
  };

  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

      // Only show button if we're not near bottom
      if (!isNearBottom) {
        setShowScrollButton(true);

        // Clear any existing timeout
        if (scrollTimeout) {
          clearTimeout(scrollTimeout);
        }

        // Set new timeout to hide button after scrolling stops
        const timeout = setTimeout(() => {
          setShowScrollButton(false);
        }, 1500); // Hide after 1.5 seconds of no scrolling

        setScrollTimeout(timeout);
      } else {
        setShowScrollButton(false);
      }
    }
  };

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }
    };
  }, [scrollTimeout]);

  useEffect(() => {
    const container = chatContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      handleScroll(); // Initial check
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const clearSpinnerTimeouts = () => {
    spinnerTimeoutsRef.current.forEach(t => clearTimeout(t));
    spinnerTimeoutsRef.current = [];
  };

  const sendMessage = async () => {
    const startTime = Date.now();

    if (userInput.trim() === '') return;

    const currentUserMessage = userInput;

    // Start smooth animation to bottom if this is the first message
    if (messages.length === 0) {
      setInputPosition('bottom');
    }

    setMessages(prev => [...prev, { sender: 'user', text: currentUserMessage }]);
    setUserInput('');

    // Scroll after the animation starts (small delay to ensure smooth transition)
    setTimeout(() => {
      scrollToBottom();
    }, 100);

    // Reset processing stage and start spinner (backend-driven stages only)
    setIsLoading(true);
    retrievalStartedRef.current = false;
    clearSpinnerTimeouts();
    setProcessingStage('analyzing');

    // Append an empty bot message
    setMessages(prev => [...prev, { sender: 'bot', text: '', usedChunks: [] }]);

    try {
      // Get user ID from authentication utils
      const userId = getUserId();

      // Start timing the API call
      await sendChatMessage(
        {
          user_message: currentUserMessage,
          tone_of_voice: toneOfVoice,
          chat_history: convertToChatHistory(messages),
          user_id: userId,
          web_search: webSearchEnabled,
        },
        responseText => {
          // Handle analysis spinner flags from backend
          const ANALYSIS_STARTED = '__ANALYSIS_STARTED__';
          const ANALYSIS_FINISHED = '__ANALYSIS_FINISHED__';
          if (responseText.includes(ANALYSIS_STARTED) && !retrievalStartedRef.current) {
            // Keep UI in analyzing until retrieval starts
            clearSpinnerTimeouts();
            setProcessingStage('analyzing');
            responseText = responseText.split(ANALYSIS_STARTED).join('');
          }
          if (responseText.includes(ANALYSIS_FINISHED)) {
            // Do not change stage here; retrieval will update next
            responseText = responseText.split(ANALYSIS_FINISHED).join('');
          }
          // Extra safety: strip any leftover analysis markers
          responseText = responseText.replace(/__ANALYSIS_STARTED__|__ANALYSIS_FINISHED__/g, '');

          // If backend signals retrieval start, align the stage per mode
          if (responseText.includes('__RETRIEVAL_STARTED__')) {
            // Clear any pre-scheduled stages to avoid out-of-order flashes
            clearSpinnerTimeouts();
            retrievalStartedRef.current = true;
            if (webSearchEnabled) {
              setProcessingStage('collecting_results');
            } else {
              setProcessingStage('retrieving');
            }
            responseText = responseText.split('__RETRIEVAL_STARTED__').join('');
          }

          // New backend stage markers
          const ANALYZING_SOURCES = '__ANALYZING_SOURCES__';
          if (responseText.includes(ANALYZING_SOURCES)) {
            clearSpinnerTimeouts();
            setProcessingStage('analyzing_sources');
            responseText = responseText.split(ANALYZING_SOURCES).join('');
          }
          const RETRIEVING_MORE = '__RETRIEVING_MORE_SOURCES__';
          if (responseText.includes(RETRIEVING_MORE)) {
            clearSpinnerTimeouts();
            setProcessingStage('retrieving_more_sources');
            responseText = responseText.split(RETRIEVING_MORE).join('');
          }

          // Look for docs retrieved flag (remove all occurrences robustly)
          const VERIFY_FLAG = '__WEB_VERIFYING__';
          if (responseText.includes(VERIFY_FLAG)) {
            // Enter verifying stage (web only)
            clearSpinnerTimeouts();
            setProcessingStage('verifying_urls');
            responseText = responseText.split(VERIFY_FLAG).join('');
          }

          const DOCS_FLAG = '__DOCS_RETRIEVED_FLAG__';
          if (responseText.includes(DOCS_FLAG)) {
            // Retrieval finished: go to reasoning until streaming starts
            clearSpinnerTimeouts();
            setProcessingStage('reasoning');
          }
          // Remove any occurrences of the docs flag, with or without surrounding whitespace/newlines
          responseText = responseText
            .split(DOCS_FLAG)
            .join('')
            .replace(/\s*__DOCS_RETRIEVED_FLAG__\s*/g, '');

          // Check if the response contains chunks data
          const CHUNKS_MARKER = '\n###CHUNKS###';
          const COMPLETE_MARKER = '\n###COMPLETE###';

          let isCompleteMessage = false;
          if (responseText.includes(COMPLETE_MARKER)) {
            console.log('[ChatBot] Found COMPLETE_MARKER in response stream');
            isCompleteMessage = true;
            // Remove the completion marker from the response text
            responseText = responseText.replace(COMPLETE_MARKER, '');
          }

          if (responseText.includes(CHUNKS_MARKER)) {
            // Retrieval is done before CHUNKS arrives; ensure timers are cleared
            clearSpinnerTimeouts();
            // Split at the chunks marker
            const parts = responseText.split(CHUNKS_MARKER);
            const text = parts[0]; // Text content is before the marker
            let chunksJSON = parts[1] || ''; // Chunks JSON is after the marker

            // Make sure we have valid JSON by removing any other markers
            if (chunksJSON.includes(COMPLETE_MARKER)) {
              chunksJSON = chunksJSON.replace(COMPLETE_MARKER, '');
            }

            // Clean up the JSON string - remove any non-JSON content at the beginning or end
            chunksJSON = chunksJSON.trim();

            // Find the first '{' and the last '}'
            const firstBrace = chunksJSON.indexOf('{');
            const lastBrace = chunksJSON.lastIndexOf('}');

            if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
              // Extract just the valid JSON part
              chunksJSON = chunksJSON.substring(firstBrace, lastBrace + 1);
            }

            let chunksData: {
              filtered_urls?: string[];
            } = {};

            try {
              // Parse only the chunks part, not the entire response
              chunksData = JSON.parse(chunksJSON);

              // Update the message text and chunks
              setMessages(prev => {
                const updated = [...prev];
                const lastMessage = updated[updated.length - 1];
                if (lastMessage && lastMessage.sender === 'bot') {
                  lastMessage.text = text;
                  lastMessage.usedChunks = parseFilteredUrls(
                    (chunksData.filtered_urls as string[]) || [],
                  );

                  // If message is complete, save the chat
                  if (isCompleteMessage) {
                    console.log('[ChatBot] Setting complete flag in message object');
                    lastMessage.isBackendComplete = true;
                    clearSpinnerTimeouts();
                    setIsLoading(false);
                    // Auto-disable web search after completion
                    if (webSearchEnabled) {
                      setWebSearchEnabled(false);
                    }

                    // Find the preceding user message
                    let userMessage = '';
                    for (let i = updated.length - 2; i >= 0; i--) {
                      if (updated[i].sender === 'user') {
                        userMessage = updated[i].text;
                        console.log(
                          '[ChatBot] Found preceding user message:',
                          userMessage?.substring(0, 30) + '...',
                        );
                        break;
                      }
                    }

                    // Save the chat to the backend using the helper function
                    saveChatIfChanged(updated);

                    // Dispatch event for other components that might need it
                    const event = new CustomEvent('botMessageComplete', {
                      detail: {
                        botMessage: text,
                        userMessage,
                        isBackendComplete: true,
                        timestamp: Date.now(),
                        usedChunks: formatChunksForModal(lastMessage.usedChunks || []),
                      },
                    });

                    window.dispatchEvent(event);
                  }
                }
                return updated;
              });
            } catch (e) {
              console.error('Failed to parse chunks data:', e);

              // Add more detailed error diagnostics
              const errorPosition = (e as Error).message?.match(/position (\d+)/)?.[1];
              if (errorPosition) {
                const position = parseInt(errorPosition);
                const start = Math.max(0, position - 20);
                const end = Math.min(chunksJSON.length, position + 20);

                console.error(
                  `JSON error context: "${chunksJSON.substring(start, position)}[ERROR HERE]${chunksJSON.substring(position, end)}"`,
                );
                console.error(
                  `Character at error position: "${chunksJSON.charAt(position)}" (charCode: ${chunksJSON.charCodeAt(position)})`,
                );
              }

              // Log more details about the JSON string
              console.error('Chunks JSON length:', chunksJSON.length);
              console.error('Chunks JSON (first 100 chars):', chunksJSON.substring(0, 100));
              console.error(
                'Chunks JSON (last 100 chars):',
                chunksJSON.substring(chunksJSON.length - 100),
              );

              // Attempt emergency cleanup and recovery
              try {
                // Find the last valid JSON closing bracket and try to parse that
                const lastBracket = chunksJSON.lastIndexOf('}');
                if (lastBracket > 0 && lastBracket < chunksJSON.length - 1) {
                  console.warn(
                    'Attempting emergency JSON recovery by truncating at last closing bracket',
                  );
                  const truncatedJSON = chunksJSON.substring(0, lastBracket + 1);
                  chunksData = JSON.parse(truncatedJSON);
                  console.warn('Emergency JSON recovery successful');
                }
              } catch (recoveryError) {
                console.error('Emergency JSON recovery failed:', recoveryError);
                // Final fallback - create empty data structure
                chunksData = { filtered_urls: [] };
              }

              // Update just the text part
              setMessages(prev => {
                const updated = [...prev];
                const lastMessage = updated[updated.length - 1];
                if (lastMessage && lastMessage.sender === 'bot') {
                  lastMessage.text = text;
                  // If we have recovered chunks data, use it
                  lastMessage.usedChunks = parseFilteredUrls(
                    (chunksData.filtered_urls as string[]) || [],
                  );

                  // If message is complete, still trigger the event
                  if (isCompleteMessage) {
                    console.log(
                      '[ChatBot] Setting complete flag in message object (after JSON error)',
                    );
                    lastMessage.isBackendComplete = true;
                    clearSpinnerTimeouts();
                    // Auto-disable web search after completion (even after JSON recovery)
                    if (webSearchEnabled) {
                      setWebSearchEnabled(false);
                    }

                    // Find the preceding user message
                    let userMessage = '';
                    for (let i = updated.length - 2; i >= 0; i--) {
                      if (updated[i].sender === 'user') {
                        userMessage = updated[i].text;
                        console.log(
                          '[ChatBot] Found preceding user message:',
                          userMessage?.substring(0, 30) + '...',
                        );
                        break;
                      }
                    }

                    // Save the chat to the backend using the helper function
                    saveChatIfChanged(updated);

                    const event = new CustomEvent('botMessageComplete', {
                      detail: {
                        botMessage: text,
                        userMessage,
                        isBackendComplete: true,
                        timestamp: Date.now(),
                        usedChunks: formatChunksForModal(lastMessage.usedChunks || []),
                      },
                    });

                    window.dispatchEvent(event);
                  }
                }
                return updated;
              });
            }
          } else {
            // No chunks marker, just update the message text

            setMessages(prev => {
              const updated = [...prev];
              const lastMessage = updated[updated.length - 1];
              if (lastMessage && lastMessage.sender === 'bot') {
                lastMessage.text = responseText;

                // If message is complete, trigger the event
                if (isCompleteMessage) {
                  console.log('[ChatBot] Setting complete flag in plain message');
                  lastMessage.isBackendComplete = true;
                  clearSpinnerTimeouts();
                  setIsLoading(false);
                  // Auto-disable web search after completion
                  if (webSearchEnabled) {
                    setWebSearchEnabled(false);
                  }

                  // Find the preceding user message
                  let userMessage = '';
                  for (let i = updated.length - 2; i >= 0; i--) {
                    if (updated[i].sender === 'user') {
                      userMessage = updated[i].text;
                      console.log(
                        '[ChatBot] Found preceding user message:',
                        userMessage?.substring(0, 30) + '...',
                      );
                      break;
                    }
                  }

                  // Save the chat to the backend using the helper function
                  saveChatIfChanged(updated);

                  const event = new CustomEvent('botMessageComplete', {
                    detail: {
                      botMessage: responseText,
                      userMessage,
                      isBackendComplete: true,
                      timestamp: Date.now(),
                      usedChunks: formatChunksForModal([]),
                    },
                  });

                  window.dispatchEvent(event);
                }
              }
              return updated;
            });
          }
        },
      );
    } catch (error) {
      console.error('Error sending message:', error);
      // Reset processing time on error
      setProcessingTimeMs(undefined);
      setIsLoading(false);
    } finally {
      const processingTime = Date.now() - startTime;
      setProcessingTimeMs(processingTime);
      console.log('processingTime', processingTime);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const convertToChatHistory = (messages: Message[]): FeedbackChatMessage[] => {
    return messages.map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      message: msg.text,
      chunks: msg.usedChunks
        ? msg.usedChunks
            .filter(chunk => {
              // Filter out chunks with no source_url
              return chunk && chunk.source_url && chunk.source_url.trim() !== '';
            })
            .map((chunk, index) => {
              // Ensure we have a valid ID - use existing ID or generate one based on source_url and index
              const chunkId =
                chunk.id && chunk.id.trim() !== ''
                  ? chunk.id
                  : `${chunk.source_url?.replace(/[^a-zA-Z0-9]/g, '') || 'chunk'}_${index}`;

              // Only include id, source_url and title - the essential fields
              return {
                id: chunkId,
                source_url: chunk.source_url || '',
                title: chunk.title || '',
              };
            })
        : [],
    }));
  };

  return (
    <div className="flex flex-col h-full w-full max-w-[1000px] mx-auto relative overflow-hidden pb-4 px-4 sm:px-8 md:px-12 lg:px-16">
      <div
        ref={chatContainerRef}
        className={[
          'flex flex-col flex-1 overflow-y-auto w-full',
          'no-scrollbar',
          messages.length === 0 ? 'invisible' : '',
        ].join(' ')}
      >
        {messages.map((msg, index) => {
          const isLastBotMessage = index === messages.length - 1 && msg.sender === 'bot';
          return (
            <ChatMessage
              key={index}
              sender={msg.sender}
              text={msg.text}
              usedChunks={(msg.usedChunks || []).map(chunk => ({
                id: chunk.id,
                title: chunk.title,
                source_url: chunk.source_url,
              }))}
              isLoading={isLastBotMessage && isLoading && !msg.isBackendComplete}
              processingStage={
                isLastBotMessage && isLoading && !msg.isBackendComplete
                  ? processingStage
                  : undefined
              }
              isLatest={isLastBotMessage}
              processingTimeMs={isLastBotMessage && !isLoading ? processingTimeMs : undefined}
              userMessage={msg.sender === 'bot' ? messages[index - 1]?.text || '' : ''}
              completeChatHistory={convertToChatHistory(messages)}
              isBackendComplete={msg.isBackendComplete}
            />
          );
        })}
        <div ref={messagesEndRef} />
      </div>
      <div
        className="relative w-full p-2 transition-all duration-700 ease-out"
        style={{
          transform: inputPosition === 'center' ? 'translateY(-40vh)' : 'translateY(0)',
          marginTop: inputPosition === 'center' ? '-10vh' : '0',
        }}
      >
        {messages.length === 0 && (
          <div className="text-center mb-6">
            <h2 className="text-brand text-5xl font-medium">Waar kan ik je mee helpen?</h2>
          </div>
        )}
        <ChatInput
          userInput={userInput}
          onInputChange={setUserInput}
          onSubmit={handleSubmit}
          toneOfVoice={toneOfVoice}
          onToneChange={setToneOfVoice}
          showScrollButton={showScrollButton}
          onScrollToBottom={scrollToBottom}
        />

        <div className="flex justify-center w-full mt-2 mb-1">
          <p className="text-[0.65rem] text-center text-[#777777]">
            BelastingAI kan fouten maken. AI4 Accountancy gebruikt geen gebruikersdata om modellen
            te trainen.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;
