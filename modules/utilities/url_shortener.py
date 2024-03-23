import logging
import requests
from modules.configurator import get_env_var_from_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AD_SHORTNER_API = get_env_var_from_db('URL_SHORTNER_API')
AD_SHORTNER = get_env_var_from_db('URL_SHORTNER')

def get_short_url(long_url):
    if not AD_SHORTNER_API or not AD_SHORTNER:
        return long_url  

    encoded_long_url = requests.utils.quote(long_url)

    api_url = f"{AD_SHORTNER}/api?api={AD_SHORTNER_API}&url={encoded_long_url}&format=text"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  
        shortened_url = response.text
        return shortened_url.strip()  
    except requests.RequestException as e:
        logging.error(f"Failed to shorten URL: {e}")
        return long_url  
