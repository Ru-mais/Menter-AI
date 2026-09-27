# media_handling_app/views.py
import requests
import logging
from django.shortcuts import render
from gtts import gTTS
import os
import base64
from pydub import AudioSegment
import time
from user_app.models import Userinfo, SearchHistory
from django.conf import settings
import datetime
# --- language map (put this near the top of the file, after imports) ---
LANGUAGE_MAP = {
    'ar': 'Arabic',
    'bn': 'Bengali',
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'gu': 'Gujarati',
    'hi': 'Hindi',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ml': 'Malayalam',
    'mr': 'Marathi',
    'pa': 'Punjabi',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ta': 'Tamil',
    'te': 'Telugu',
    'tr': 'Turkish',
    'ur': 'Urdu',
    'vi': 'Vietnamese',
    'zh': 'Chinese',
}
# -----------------------------------------------------------------------


logger = logging.getLogger(__name__)

def create_talking_avatar(image_path, audio_path):
    """
    Create talk via d-id API. Returns result_url or None.
    Use settings.DID_API_KEY for Basic Auth.
    """
    try:
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            logger.error("Image or audio file missing for avatar creation.")
            return None

        # Get list of keys from settings
        did_api_keys = getattr(settings, "DID_API_KEYS", [])
        
        # If no list, check for single key
        if not did_api_keys:
            single_key = getattr(settings, "DID_API_KEY", None)
            if single_key:
                did_api_keys = [single_key]
        
        if not did_api_keys:
            logger.error("No D-ID API keys found in settings.")
            return None

        logger.info(f"Found {len(did_api_keys)} D-ID API keys. Starting rotation if needed.")

        last_error = None
        
        # Helper function to perform the actual API calls with a specific key
        def try_create_talk_with_key(api_key):
            # Prepare Basic Auth Encoded Header
            auth_string = f"{api_key}"
            encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            auth_header = f"Basic {encoded_auth}"
            
            # 1. Upload Image
            image_url = None
            try:
                url_img = "https://api.d-id.com/images"
                headers_img = {"Authorization": auth_header}
                with open(image_path, "rb") as f:
                    files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
                    resp_img = requests.post(url_img, headers=headers_img, files=files, timeout=30)
                
                if resp_img.status_code == 201:
                    image_url = resp_img.json().get("url")
                    logger.info("D-ID Image uploaded: %s", image_url)
                else:
                    logger.error("D-ID Image upload failed: %s %s", resp_img.status_code, resp_img.text)
                    return None, f"Image upload failed: {resp_img.status_code}"
            except Exception as e:
                logger.exception("Exception uploading image to D-ID: %s", e)
                return None, str(e)

            # 2. Upload Audio
            audio_url = None
            try:
                url_aud = "https://api.d-id.com/audios"
                headers_aud = {"Authorization": auth_header}
                with open(audio_path, "rb") as f:
                    files = {"audio": (os.path.basename(audio_path), f, "audio/mpeg")}
                    resp_aud = requests.post(url_aud, headers=headers_aud, files=files, timeout=30)
                
                if resp_aud.status_code == 201:
                    audio_url = resp_aud.json().get("url")
                    logger.info("D-ID Audio uploaded: %s", audio_url)
                else:
                    logger.error("D-ID Audio upload failed: %s %s", resp_aud.status_code, resp_aud.text)
                    return None, f"Audio upload failed: {resp_aud.status_code}"
            except Exception as e:
                logger.exception("Exception uploading audio to D-ID: %s", e)
                return None, str(e)

            # 3. Create Talk
            url_talks = "https://api.d-id.com/talks"
            headers_talks = {
                "Authorization": auth_header,
                "Content-Type": "application/json"
            }
            data = {
                "source_url": image_url,
                "script": {
                    "type": "audio",
                    "audio_url": audio_url
                },
                "config": {
                    "fluent": True
                }
            }
            
            resp = requests.post(url_talks, headers=headers_talks, json=data, timeout=30)
            if resp.status_code >= 400:
                logger.error("D-ID create talk failed: %s %s", resp.status_code, resp.text[:400])
                if resp.status_code in [401, 402, 403, 429]: # Auth error, Payment required, Forbidden, Too Many Requests
                     return None, "ROTATE_KEY" # Signal to rotate key
                return None, f"Create talk failed: {resp.status_code}"

            talk_id = resp.json().get("id")
            if not talk_id:
                logger.error("No talk id returned from D-ID: %s", resp.text[:400])
                return None, "No talk ID"

            # 4. Poll for result
            poll_url = f"https://api.d-id.com/talks/{talk_id}"
            # Start polling
            for attempt in range(20):
                time.sleep(2)
                poll_resp = requests.get(poll_url, headers=headers_talks, timeout=20)
                if poll_resp.status_code == 200:
                    poll_data = poll_resp.json()
                    status = poll_data.get("status")
                    result_url = poll_data.get("result_url")
                    
                    if status == "done" and result_url:
                        logger.info("D-ID video ready: %s", result_url)
                        return result_url, None
                    elif status == "error":
                        logger.error("D-ID processing error: %s", poll_data)
                        return None, f"Processing error: {poll_data}"
                else:
                     logger.debug("D-ID poll status: %s - %s", poll_resp.status_code, poll_resp.text[:200])
            
            logger.warning("D-ID video not ready after polling.")
            return None, "Timeout polling"


        # --- Main Rotation Loop ---
        for i, key in enumerate(did_api_keys):
            masked_key = key[:5] + "..." if len(key) > 5 else "***"
            logger.info(f"Attempting D-ID generation with key #{i+1} ({masked_key})")
            
            result_url, error = try_create_talk_with_key(key)
            
            if result_url:
                return result_url
            
            if error == "ROTATE_KEY":
                logger.warning(f"Key #{i+1} failed with rotateable error. Trying next key...")
                last_error = error
                continue
            else:
                # Non-rotateable error (e.g. image missing, timeouts that aren't strict auth failures?)
                # Actually, for robustness, maybe we should try next key for ANY failure except missing local files?
                # But for now let's stick to auth/rate limit errors triggering rotation, 
                # or maybe just keep trying? 
                # Let's keep trying for robustness!
                logger.warning(f"Key #{i+1} failed with error: {error}. Trying next key just in case.")
                last_error = error
                continue

        logger.error("All D-ID keys failed. Last error: %s", last_error)
        return None
    except Exception as e:
        logger.exception("Exception in create_talking_avatar: %s", e)
        return None

# Together AI API key fallback to settings if set
#API_KEY = getattr(settings, "TOGETHER_API_KEY", "7d33c4c21a3ab7ce946e1ec3f311a61ccc8f724cefd0fab92ad8b116fbf88db3")

# Replace existing generate_response() with this Groq version
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 
import requests, logging
logger = logging.getLogger(__name__)

def generate_response_debug(prompt):
    GROQ_KEY = "<your-key-or-read-from-settings>"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",   # your model to test
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        # Do NOT raise_for_status yet — print the response body for debugging
        print("STATUS:", r.status_code)
        print("RESPONSE TEXT:", r.text)
        # now raise if you want the exception
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.exception("Groq debug request failed")
        return {"error": str(e)}


def generate_response(prompt):
    """
    Generate AI response using Groq API.
    Uses GROQ_API_KEY from settings.
    """
    # Try to get API key from settings or environment variable
    API_KEY = getattr(settings, "GROQ_API_KEY", None)
    if not API_KEY:
        # Fallback to environment variable
        import os
        API_KEY = os.environ.get("GROQ_API_KEY", None)
    
    if not API_KEY:
        logger.error("GROQ_API_KEY not found in settings or environment")
        return "Error: API key not configured. Please set GROQ_API_KEY in settings or environment variables."
    
    # Log first few characters for debugging (don't log full key for security)
    logger.debug("Using API key starting with: %s...", API_KEY[:10] if len(API_KEY) > 10 else "***")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Try different Groq models - some may be deprecated
    models_to_try = [
        "llama-3.3-70b-versatile",  # Newer model
        "llama-3.1-70b-versatile",  # Alternative
        "mixtral-8x7b-32768",       # Alternative model name format
        "mistralai/Mixtral-8x7B-Instruct-v0.1",  # Original
    ]
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    # Try each model until one works
    for model in models_to_try:
        data["model"] = model
        try:
            logger.debug("Trying model: %s", model)
            logger.debug("Sending request to %s", url)
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            logger.debug("Response status code: %s", response.status_code)
            
            if response.status_code == 401:
                # If 401, the API key is invalid - don't try other models
                error_detail = response.text
                logger.error("401 Unauthorized - API key invalid. Response: %s", error_detail[:200])
                return f"Error: Invalid API key. Please check your GROQ_API_KEY in settings. The API key may be expired or incorrect. Please get a new key from https://console.groq.com/"
            elif response.status_code == 429:
                logger.warning("429 Too Many Requests (Rate limit hit)")
                return "Our AI mentors are currently busy helping others, please try again in a minute."
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                if "message" in result["choices"][0]:
                    logger.info("Successfully generated response using model: %s", model)
                    return result["choices"][0]["message"]["content"]
            
            logger.warning("Could not parse response for model %s: %s", model, result)
            # Continue to next model
            
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                # Don't try other models if it's an auth error
                error_detail = err.response.text if hasattr(err.response, 'text') else str(err)
                logger.error("401 Unauthorized - API key invalid. Response: %s", error_detail[:200])
                return f"Error: Invalid API key. Please check your GROQ_API_KEY in settings. The API key may be expired or incorrect. Please get a new key from https://console.groq.com/"
            elif err.response.status_code == 429:
                logger.warning("429 Too Many Requests (Rate limit hit) captured in HTTPError")
                return "Our AI mentors are currently busy helping others, please try again in a minute."
            logger.warning("HTTP error with model %s: %s", model, err)
            # Try next model
            continue
        except Exception as err:
            logger.warning("Error with model %s: %s", model, err)
            # Try next model
            continue
    
    # If all models failed
    logger.error("All models failed to generate response")
    return "Error: Unable to generate response. Please check your API key and try again."


def search(request):
    """
    Single, robust search view:
    - Handles anonymous users safely
    - Normalizes membership type (case-insensitive)
    - Uses safe default for attempts
    """
    logger.debug("Request method: %s", request.method)
    logger.debug("POST data: %s", request.POST)

    context = {}
    user = None
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = Userinfo.objects.get(id=user_id)
            context['first_name'] = user.first_name or "Guest"
        except Userinfo.DoesNotExist:
            user = None
            context['first_name'] = "Guest"
    else:
        context['first_name'] = "Guest"

    if user:
        credits = user.credits
    else:
        credits = 0
    
    context['remaining_prompts'] = credits
    context['remaining_credits'] = credits

    # default language
    language = 'en'
    if request.method == "POST":
        prompt = request.POST.get('topic')
        language = request.POST.get('language', 'en')
        logger.debug("Prompt=%s language=%s", prompt, language)

        if not prompt:
            logger.warning("No prompt provided.")
            context['error'] = 'Please provide a valid prompt.'
            return render(request, 'search.html', context)

        # Determine user's credits
        if user:
            credits = user.credits
        else:
            credits = 0

        # If user has enough credits (1 for text)
        if credits >= 1:
            language_name = LANGUAGE_MAP.get(language, 'English')
            if language != 'en':
                full_prompt = f"Explain about '{prompt}' completely in {language_name}."
            else:
                full_prompt = f"Explain about '{prompt}' completely in English."

            generated_text = generate_response(full_prompt)

            # convert to audio
            try:
                tts = gTTS(text=generated_text, lang=language)
                audio_file = os.path.join("static", "audio", "explanation.mp3")
                os.makedirs(os.path.dirname(audio_file), exist_ok=True)
                tts.save(audio_file)

                # Cut audio to first 3 minutes before sending to D-ID API
                try:
                    audio_segment = AudioSegment.from_file(audio_file)
                    three_minutes = 2.5 * 60 * 1000
                    if len(audio_segment) > three_minutes:
                        short_audio = audio_segment[:three_minutes]
                        short_audio.export(audio_file, format="mp3")
                except Exception as e:
                    logger.exception("Failed to cut audio with pydub: %s", e)

            except Exception as e:
                logger.exception("gTTS failed: %s", e)
                audio_file = None

            avatar_video_url = None
            # Commenting out D-ID Avatar generation to save API usage/costs
            # if audio_file:
            #     avatar_video_url = create_talking_avatar(os.path.join("static", "images", "images.jpeg"), audio_file)

            # Log text API usage
            if user:
                from user_app.models import APIUsage, ChatSession, ChatMessage
                APIUsage.objects.create(
                    user=user,
                    endpoint='groq_chat',
                    success=True,
                    cost=1.0
                )
                
                if avatar_video_url:
                    APIUsage.objects.create(
                        user=user,
                        endpoint='did_avatar',
                        success=True,
                        cost=5.0
                    )
            
            # decrease credits and save if we have a user object
            if user:
                user.credits = max(credits - 1, 0)
                
                # Save to history
                history_entry = {
                    'prompt': prompt,
                    'answer': generated_text,
                    'is_dict': True, # flag for template backward compatibility
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                # Initialize list if None
                if not user.recent_searches:
                    user.recent_searches = []
                
                # Add to beginning
                if isinstance(user.recent_searches, list):
                    user.recent_searches.insert(0, history_entry)
                    # Keep last 20
                    user.recent_searches = user.recent_searches[:20]
                
                try:
                    user.save()
                    SearchHistory.objects.create(
                        user=user,
                        prompt=prompt,
                        answer=generated_text
                    )
                    
                    # Create ChatSession and ChatMessage as requested
                    session, created = ChatSession.objects.get_or_create(
                        user=user,
                        title=prompt[:50] + "..."
                    )
                    ChatMessage.objects.create(session=session, role='user', content=prompt)
                    ChatMessage.objects.create(session=session, role='ai', content=generated_text)
                    
                except Exception as e:
                    logger.exception("Failed to save user credits/history: %s", e)

            context['remaining_prompts'] = user.credits if user else 0
            context['remaining_credits'] = user.credits if user else 0
            context['explanation'] = generated_text
            context['audio_url'] = f"/{audio_file}" if audio_file else None
            context['avatar_video_url'] = avatar_video_url
            context['topic'] = prompt
        else:
            logger.warning("User has not enough credits left.")
            context['error'] = "You do not have enough credits (1 required). Please upgrade your plan."
            context['remaining_prompts'] = credits
            context['remaining_credits'] = credits

    return render(request, 'search.html', context)