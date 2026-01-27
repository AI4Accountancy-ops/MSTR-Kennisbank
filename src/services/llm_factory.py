import logging
from typing import Any, Dict, List, Type, Generator

import instructor
from openai import AzureOpenAI
from pydantic import BaseModel, Field

import definitions.names as n
from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMFactory:
    def __init__(self, provider: str):
        self.provider = provider
        self.settings = getattr(get_settings(), provider)
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        client_initializers = {
            n.AZURE_OPENAI: lambda s: instructor.from_openai(
                AzureOpenAI(
                    api_key=s.api_key,
                    api_version=s.api_version,
                    azure_endpoint=s.api_base,
                )
            ),
        }

        initializer = client_initializers.get(self.provider)
        if initializer:
            return initializer(self.settings)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def normal_completion(
            self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs
    ) -> Any:
        completion_params = {
            n.MODEL: kwargs.get(n.MODEL, self.settings.default_model),
            n.MAX_RETRIES: kwargs.get(n.MAX_RETRIES, self.settings.max_retries),
            n.RESPONSE_MODEL: response_model,
            n.MESSAGES: messages,
        }
        response = self.client.chat.completions.create(**completion_params)
        return response

    def create_completion(
        self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs
    ) -> Any:
        completion_params = {
            n.MODEL: kwargs.get(n.MODEL, self.settings.default_model),
            n.MAX_RETRIES: kwargs.get(n.MAX_RETRIES, self.settings.max_retries),
            n.RESPONSE_MODEL: response_model,
            n.MESSAGES: messages,
        }
        # Include optional parameters only when explicitly provided
        if n.REASONING_EFFORT in kwargs and kwargs.get(n.REASONING_EFFORT) is not None:
            completion_params[n.REASONING_EFFORT] = kwargs.get(n.REASONING_EFFORT)
        # Optional tool calling support
        if "tools" in kwargs and kwargs["tools"] is not None:
            completion_params["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs and kwargs["tool_choice"] is not None:
            completion_params["tool_choice"] = kwargs["tool_choice"]
        response = self.client.chat.completions.create(**completion_params)
        return response
        
    def stream_completion(
        self, 
        response_model: Type[BaseModel], 
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[BaseModel, None, None]:
        completion_params = {
            n.MODEL: kwargs.get(n.MODEL, self.settings.default_model),
            n.MAX_RETRIES: kwargs.get(n.MAX_RETRIES, self.settings.max_retries),
            n.RESPONSE_MODEL: response_model,
            n.MESSAGES: messages,
            n.STREAM: True
        }
        # Include optional parameters only when explicitly provided
        if n.REASONING_EFFORT in kwargs and kwargs.get(n.REASONING_EFFORT) is not None:
            completion_params[n.REASONING_EFFORT] = kwargs.get(n.REASONING_EFFORT)
        # Optional tool calling support
        if "tools" in kwargs and kwargs["tools"] is not None:
            completion_params["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs and kwargs["tool_choice"] is not None:
            completion_params["tool_choice"] = kwargs["tool_choice"]

        stream = self.client.chat.completions.create_partial(**completion_params)

        dummy = response_model.model_construct() if hasattr(response_model, 'model_construct') else response_model()
        field_names = list(dummy.model_dump().keys() if hasattr(dummy, 'model_dump') else dummy.dict().keys())

        for chunk in stream:
            if field_names and not all(hasattr(chunk, field) for field in field_names):
                empty_values = {field: "" for field in field_names}
                empty_chunk = response_model(**empty_values)
                yield empty_chunk
            else:
                yield chunk


# Example of usage
if __name__ == "__main__":

    class CompletionResponseExample(BaseModel):
        response: str = Field(description="Your response to the user")
        reasoning: str = Field(description="Explain the reasoning behind your response")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can answer questions and help with tasks.",
        },
        {"role": "user", "content": "What is the capital of the moon?"},
    ]

    llm = LLMFactory(n.AZURE_OPENAI)
    
    # Example 1: Regular completion (final result only)
    logger.info("Example 1: Regular completion")
    completion_params = {
        n.MODEL: llm.settings.default_model,
        n.MAX_RETRIES: llm.settings.max_retries,
        n.REASONING_EFFORT: llm.settings.reasoning_effort,
        n.RESPONSE_MODEL: CompletionResponseExample,
        n.MESSAGES: messages,
    }
    response = llm.client.chat.completions.create(**completion_params)
    logger.info(f"Response: {response.response}\n")
    logger.info(f"Reasoning: {response.reasoning}\n")
    
    # Example 2: Using a custom streaming method for LLMFactory
    logger.info("\nExample 2: Using a custom streaming method for LLMFactory")
    
    # Get the generator
    stream_generator = llm.stream_completion(
        response_model=CompletionResponseExample,
        messages=messages,
    )

    print("\nProcessing stream (this may take a moment)...")
    
    # Iterate through the generator
    final_chunk = None
    for chunk in stream_generator:
        # Print the response
        print(f"{chunk.response}")
        final_chunk = chunk
    
    # Log the final result
    logger.info("\nStream completed")
    logger.info(f"Final response: {final_chunk.response}")
    logger.info(f"Final reasoning: {final_chunk.reasoning}")
