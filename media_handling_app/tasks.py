from celery import shared_task
from django.conf import settings
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)

@shared_task
def generate_ai_response_task(prompt):
    # Try to fetch from cache first
    cache_key = f"ai_response_{hash(prompt)}"
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info("Cache hit for AI response")
        return cached_response

    # Similar logic to generate_response but using Celery
    import os
    API_KEY = getattr(settings, "GROQ_API_KEY", None)
    if not API_KEY:
        API_KEY = os.environ.get("GROQ_API_KEY", None)
        
    if not API_KEY:
        return "Error: API key not configured."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768",
    ]
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    for model in models_to_try:
        data["model"] = model
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 401:
                return "Error: Invalid API key."
            elif response.status_code == 429:
                return "Our AI mentors are currently busy helping others, please try again in a minute."
                
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                # Save to cache for 1 hour
                cache.set(cache_key, answer, timeout=3600)
                return answer
                
        except requests.exceptions.HTTPError as err:
            continue
        except Exception as err:
            continue
            
    # Fallback to HuggingFace or OpenAI if Groq fails
    # Placeholder for fallback logic
    return "Error: Unable to generate response."
