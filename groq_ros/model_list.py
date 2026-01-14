import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_groq_models():
    try:
        models = client.models.list()
        print(f"{'Model ID':<40} | {'Owned By':<10}")
        print("-" * 55)
        
        for model in sorted(models.data, key=lambda x: x.id):
            print(f"{model.id:<40} | {model.owned_by:<10}")   
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    get_groq_models()