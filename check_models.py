from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# 1. Setup your API Key
# Using GEMINI_API_KEY to match your project's config
api_key = os.getenv("GEMINI_API_KEY") 

# If you don't have an env variable set, uncomment the line below and paste your key:
# api_key = "PASTE_YOUR_KEY_HERE"

if not api_key:
    raise ValueError("No API Key provided. Please set GEMINI_API_KEY in your .env file.")

# Configure the new google.genai client
client = genai.Client(api_key=api_key)

print(f"{'Model Name':<50} | {'Capabilities'}")
print("-" * 80)

try:
    # 2. List the models using the new API
    models = client.models.list()
    
    for model in models:
        name = model.name
        
        # Check capabilities from the model object
        capabilities = []
        
        # The new API structure is different - models have different properties
        if hasattr(model, 'supported_generation_methods'):
            methods = model.supported_generation_methods
            if 'generateContent' in methods:
                capabilities.append("Generate Content")
            if 'embedContent' in methods:
                capabilities.append("Embeddings")
        else:
            # For newer API, check model name patterns
            if 'embedding' in name.lower():
                capabilities.append("Embeddings")
            elif 'gemini' in name.lower():
                capabilities.append("Generate Content (Text/Image/Video)")
            
        print(f"{name:<50} | {', '.join(capabilities) if capabilities else 'Check documentation'}")

except Exception as e:
    print(f"Error fetching models: {e}")
    print("Please check that your API key is valid.")
    import traceback
    traceback.print_exc()
