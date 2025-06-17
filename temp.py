# from g4f.client import Client

# client = Client()
# response = client.images.generate(
#     model="flux",
#     prompt="a white siamese cat",
#     response_format="url"
# )

# print(f"Generated image URL: {response.data[0].url}")

from g4f.client import Client

client = Client()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    web_search=False
)
print(response.choices[0].message.content)