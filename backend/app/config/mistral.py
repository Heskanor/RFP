import os
from mistralai import Mistral

mistral_client = Mistral(api_key= os.getenv("MISTRAL_API_KEY"))
