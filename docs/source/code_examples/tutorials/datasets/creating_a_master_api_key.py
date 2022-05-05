from encord.user_client import EncordUserClient

user_client = EncordUserClient.create_with_ssh_private_key(
    "<your_private_key>"
)
dataset_api_key = user_client.get_or_create_dataset_api_key(
    "<dataset_hash>"
)
print(dataset_api_key)
