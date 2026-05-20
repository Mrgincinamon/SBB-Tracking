"""Quick smoke test: does the Anthropic API work with our .env setup?"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

key = os.getenv("ANTHROPIC_API_KEY")
model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
assert key, "ANTHROPIC_API_KEY fehlt in .env"

print(f"Model: {model}")
print(f"Key endet auf: ...{key[-6:]}")

client = Anthropic()  # liest ANTHROPIC_API_KEY aus env automatisch
msg = client.messages.create(
    model=model,
    max_tokens=100,
    temperature=0,
    messages=[
        {"role": "user", "content": "Antworte auf deutsch in EINEM Satz: "
         "Warum sind Schweizer Zuege normalerweise puenktlich?"}
    ],
)
print("\n--- Antwort ---")
print(msg.content[0].text)
print(f"\nInput-Tokens: {msg.usage.input_tokens}")
print(f"Output-Tokens: {msg.usage.output_tokens}")
# Sonnet 4.6 pricing: $3/Mio in, $15/Mio out
cost = (msg.usage.input_tokens / 1e6 * 3.0
        + msg.usage.output_tokens / 1e6 * 15.0)
print(f"Geschaetzte Kosten: ${cost:.6f}")
