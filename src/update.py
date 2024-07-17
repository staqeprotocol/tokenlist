from web3 import Web3
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

version = ""

chains = {
    534351: {
        "rpc_url": "https://sepolia-rpc.scroll.io",
        "contract_address": "0x9cbD0A9D9fb8e8c1baA4687E4e8068aDA57a220f"
    },
    1029: {
        "rpc_url": "https://pre-rpc.bittorrentchain.io",
        "contract_address": "0x9cbD0A9D9fb8e8c1baA4687E4e8068aDA57a220f"
    },
    97: {
        "rpc_url": "https://data-seed-prebsc-1-s1.bnbchain.org:8545",
        "contract_address": "0x9cbD0A9D9fb8e8c1baA4687E4e8068aDA57a220f"
    }
}

contract_abi = [
    {
        "type": "function",
        "name": "getTotalPools",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "tokenURI",
        "inputs": [{"name": "tokenId", "type": "uint256", "internalType": "uint256"}],
        "outputs": [{"name": "", "type": "string", "internalType": "string"}],
        "stateMutability": "view"
    }
]

def fetch_ipfs_metadata(ipfs_hash):
    if ipfs_hash.startswith("ipfs://"):
        ipfs_hash = ipfs_hash[7:]
    url = f'https://ipfs.io/ipfs/{ipfs_hash}'
    print(f"Fetching IPFS URL: {url}")  # Debugging line
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def update_token_list(chain_id, new_tokens):
    token_list_path = Path(f'./chains/{chain_id}.tokenlist.json')
    token_list_path.parent.mkdir(parents=True, exist_ok=True)
    
    if token_list_path.exists():
        with open(token_list_path, 'r') as file:
            token_list = json.load(file)
        existing_addresses = {token['address'] for token in token_list['tokens']}
    else:
        token_list = {
            "name": "Staqe Protocol",
            "logoURI": "https://bafybeibkoohmrfcoltp63ga7c63ww5v45pupm22pavminkzgxgqq7cmd5q.ipfs.dweb.link",
            "keywords": ["stake", "pool"],
            "tags": {
                "staqe": {
                    "name": "Staqe Protocol",
                    "description": "Tokens used to create a pool in Staqe.App"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tokens": [],
            "version": {"major": 0, "minor": 0, "patch": 0}
        }
        existing_addresses = set()

    for token in new_tokens:
        if token['address'] not in existing_addresses:
            token_list['tokens'].append(token)
            existing_addresses.add(token['address'])

    token_list['version']['patch'] += 1
    token_list['timestamp'] = datetime.now(timezone.utc).isoformat()
    with open(token_list_path, 'w') as file:
        json.dump(token_list, file, indent=4)

    v = token_list['version']

    return f"{v['major']}.{v['minor']}.{v['patch']}"

errors = []

for chain_id, chain_details in chains.items():
    w3 = Web3(Web3.HTTPProvider(chain_details['rpc_url']))
    contract = w3.eth.contract(address=chain_details['contract_address'], abi=contract_abi)

    total_pools = contract.functions.getTotalPools().call()

    all_tokens = []
    added_addresses = set()

    for i in range(1, total_pools + 1):
        try:
            ipfs_hash = contract.functions.tokenURI(i).call()
            # Check for and skip incorrect IPFS URL prefixes
            if ipfs_hash.startswith("_ipfs://"):
                errors.append(f"Skipping invalid IPFS hash for tokenId {i}: {ipfs_hash}")
                continue
            # Remove any incorrect prefix that might have been added
            if not ipfs_hash.startswith("ipfs://"):
                ipfs_hash = f"ipfs://{ipfs_hash}"
            metadata = fetch_ipfs_metadata(ipfs_hash)
            tokens = metadata.get("tokens", [])
            for token in tokens:
                if token["address"] not in added_addresses:
                    all_tokens.append({
                        "chainId": chain_id,
                        "address": token["address"],
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "decimals": token["decimals"],
                        "logoURI": token["logoURI"],
                        "tags": token["tags"]
                    })
                    added_addresses.add(token["address"])
        except requests.exceptions.RequestException as e:
            errors.append(f"HTTP error for tokenId {i}: {str(e)}")
        except json.JSONDecodeError as e:
            errors.append(f"JSON decode error for tokenId {i}: {str(e)}")
        except Exception as e:
            errors.append(f"Failed to fetch tokenURI for tokenId {i}: {str(e)}")

    version = update_token_list(chain_id, all_tokens)

print(version)
if errors:
    print("Errors encountered:")
    for error in errors:
        print(error)
