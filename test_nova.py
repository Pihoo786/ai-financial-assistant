import boto3
import json

client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

message = {
    "role": "user",
    "content": [{"text": "Hello! Can you introduce yourself briefly?"}]
}

response = client.invoke_model(
    modelId="amazon.nova-lite-v1:0",
    body=json.dumps({
        "messages": [message],
        "inferenceConfig": {
            "maxTokens": 200
        }
    })
)

result = json.loads(response["body"].read())
print(result["output"]["message"]["content"][0]["text"])