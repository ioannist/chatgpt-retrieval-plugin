import os
from typing import List, Dict, Any, Tuple
import openai

from tenacity import retry, wait_random_exponential, stop_after_attempt

openai.api_key = os.environ["OPENAI_API_KEY"]

@retry(wait=wait_random_exponential(min=20, max=60), stop=stop_after_attempt(3))
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Embed texts using OpenAI's ada model.

    Args:
        texts: The list of texts to embed.

    Returns:
        A list of embeddings, each of which is a list of floats.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    if len(texts) == 0:
        return []
    
    # Call the OpenAI API to get the embeddings
    response = openai.Embedding.create(input=texts, model="text-embedding-ada-002")

    # Extract the embedding data from the response
    data = response["data"]  # type: ignore

    # Return the embeddings as a list of lists of floats
    return [result["embedding"] for result in data]


@retry(wait=wait_random_exponential(min=20, max=60), stop=stop_after_attempt(3))
def get_chat_completion(
    messages,
    model="gpt-4",  # use "gpt-4" for better results
):
    """
    Generate a chat completion using OpenAI's chat completion API.

    Args:
        messages: The list of messages in the chat history.
        model: The name of the model to use for the completion. Default is gpt-4, which is a fast, cheap and versatile model. Use gpt-4 for higher quality but slower results.

    Returns:
        A string containing the chat completion.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    # call the OpenAI chat completion API with the given messages
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
    )

    choices = response["choices"]  # type: ignore
    completion = choices[0].message.content.strip()
    print(f"Completion: {completion}")
    return completion


def ask_with_chunks(question: str, chunks: List[str], prev_messages: List[Any] = []) -> Tuple[Dict[str, Any], List[Any]]:
    """
    Call chatgpt api with user's question and retrieved chunks.
    """
    # Send a request to the GPT-3 API
    if len(prev_messages) > 0:
        messages = prev_messages;
    else:
        messages = [
            {"role": "system", "content": "You are helping find, extract and synthesize information from longer texts. You are succinct and always change the extracted content to make it unique."},
        ]
    messages.extend(list(
        map(lambda chunk: {
            "role": "user",
            "content": chunk
        }, chunks)))
    
    prompt = f"""
        By considering above input, answer the question without copying any text or infringing copyright: {question}
    """

    messages.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,  # High temperature leads to a more creative response.
    )
    answer = response["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": answer})
    return (answer, messages)
    