from web3 import Web3

from .config import settings


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def get_fa_balance(wallet_address: str) -> float:
    if not settings.web3_rpc_url or not settings.fa_token_contract:
        raise ValueError("WEB3_RPC_URL and FA_TOKEN_CONTRACT must be configured")

    web3 = Web3(Web3.HTTPProvider(settings.web3_rpc_url))
    if not web3.is_connected():
        raise ConnectionError("Cannot connect to RPC node")

    checksum_wallet = web3.to_checksum_address(wallet_address)
    checksum_contract = web3.to_checksum_address(settings.fa_token_contract)
    contract = web3.eth.contract(address=checksum_contract, abi=ERC20_ABI)
    raw_balance = contract.functions.balanceOf(checksum_wallet).call()
    return round(raw_balance / (10 ** settings.fa_token_decimals), 6)

