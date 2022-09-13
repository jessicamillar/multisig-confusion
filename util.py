"""Much of this comes from https://github.com/algorand/auction-demo/blob/main/auction/util.py,

"""
import json
from functools import cached_property
import logging
from hashlib import shake_256
from typing import List, Tuple, Dict, Any, Optional, Union
import base64
from functools import cached_property
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk import encoding, account, mnemonic
from algosdk.kmd import KMDClient
import algosdk.error
from pyteal import compileTeal, Mode, Expr


from settings import Settings


def print_created_asset(algodclient, accountAddress, assetid):    
    # note: if you have an indexer instance available it is easier to just use this
    # response = myindexer.accounts(asset_id = assetid)
    # then use 'account_info['created-assets'][0] to get info on the created asset
    account_info = algodclient.account_info(accountAddress)
    idx = 0;
    for my_account_info in account_info['created-assets']:
        scrutinized_asset = account_info['created-assets'][idx]
        idx = idx + 1       
        if (scrutinized_asset['index'] == assetid):
            print("Asset ID: {}".format(scrutinized_asset['index']))
            print(json.dumps(my_account_info['params'], indent=4))
            break
    
def print_asset_holding(algodclient, account, assetid):
    # note: if you have an indexer instance available it is easier to just use this
    # response = myindexer.accounts(asset_id = assetid)
    # then loop thru the accounts returned and match the account you are looking for
    account_info = algodclient.account_info(account)
    idx = 0
    for my_account_info in account_info['assets']:
        scrutinized_asset = account_info['assets'][idx]
        idx = idx + 1        
        if (scrutinized_asset['asset-id'] == assetid):
            print("Asset ID: {}".format(scrutinized_asset['asset-id']))
            print(json.dumps(scrutinized_asset, indent=4))
            break


LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) " "-35s %(lineno) -5d: %(message)s"
)
LOGGER = logging.getLogger(__name__)


ZERO_ADDRESS = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"


def string_2_32byte_hash(input_str: str):
    return shake_256(input_str.encode("utf-8")).digest(32)


def string_2_AlgoAddress(input_str: str):
    fakeHash1 = string_2_32byte_hash(input_str)
    fakeHash1_as_address = encoding.encode_address(fakeHash1)
    assert encoding.is_valid_address(fakeHash1_as_address)
    return fakeHash1_as_address


def getAlgodClient(settings: Settings) -> AlgodClient:
    LOGGER.debug(
        "Setting up an AlgodClient, using algod token and algod address from Settings."
        f"e.g., algod address is {settings.algod_address} "
    )
    return AlgodClient(settings.algod_token.get_secret_value(), settings.algod_address)


def getKMDClient(settings: Settings) -> KMDClient:
    return KMDClient(settings.kmd_token.get_secret_value(), settings.kmd_address)


def addressToPublicKey(addr: str) -> str:
    return base64.b32encode(encoding.decode_address(addr)).decode()


def publicKeyToAddress(pubKey: str) -> str:
    return encoding.encode_address(base64.b32decode(pubKey))




class AlgoAccount:
    """Representation of the public and private information of an Algorand
    account, with extra documentation.

    sk - the private signing key of the account
    addr - the public address of the account. Essentially the public
    key, massaged to reduce human error

    generated by passing the private key. If none is passed
    it will generate a new one
    """

    def __init__(self, privateKey: Optional[str] = None) -> None:
        if privateKey is None:
            privateKey = account.generate_account()[0]
        self.sk: str = privateKey
        self.addr: str = account.address_from_private_key(privateKey)

    def address(self) -> str:
        return self.addr

    def getPrivateSigningKey(self) -> str:
        return self.sk

    def getPublicKey(self) -> str:
        """For reasons that include the need to make the keys human-readable and robust
        to human error when transferred, both the public and private keys undergo
        transformation. The public key is transformed into an Algorand address,
        by adding a 4-byte checksum to the end of the public key and then encoding it
        in base32. The result is what both the developer and end-user recognize as an
        Algorand address. The address is 58 characters long.

        See the docs: https://developer.algorand.org/docs/get-details/accounts/
        """
        return addressToPublicKey(self.addr)

    def getMnemonic(self) -> str:
        return mnemonic.from_private_key(self.sk)

    @cached_property
    def m(self) -> str:
        """m stands for `mnemonic`, the string of 25 words
        that has equivalent information content to the private key
        """
        return self.getMnemonic()

    @cached_property
    def publicKey(self):
        return self.getPublicKey()

    @cached_property
    def privateSigningKey(self) -> str:
        """The private signing key (type str, len 88) for the account.
        Equivalent in information content to the mnemonic. Should
        be kept private. Can generate the address and the public key.

        Returns:
            _type_: _description_
        """
        return self.sk
    
    @cached_property
    def addrShortHand(self) -> str:
        """Returns the last 6 characters of the account address.
        
        This is just used for logging messages and human eyes!
        """
        return self.addr[-6:]

    @classmethod
    def FromMnemonic(cls, m: str) -> "AlgoAccount":
        return cls(mnemonic.to_private_key(m))


class PendingTxnResponse:
    def __init__(self, txID: str, response: Dict[str, Any]) -> None:
        self.txID = txID
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.applicationIndex: Optional[int] = response.get("application-index")
        self.assetIndex: Optional[int] = response.get("asset-index")
        self.closeRewards: Optional[int] = response.get("close-rewards")
        self.closingAmount: Optional[int] = response.get("closing-amount")
        self.confirmedRound: Optional[int] = response.get("confirmed-round")
        self.globalStateDelta: Optional[Any] = response.get("global-state-delta")
        self.localStateDelta: Optional[Any] = response.get("local-state-delta")
        self.receiverRewards: Optional[int] = response.get("receiver-rewards")
        self.senderRewards: Optional[int] = response.get("sender-rewards")

        self.innerTxns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [base64.b64decode(l) for l in response.get("logs", [])]


def waitForTransaction(client: AlgodClient, txID: str, timeout: int = 10) -> PendingTxnResponse:
    lastStatus = client.status()
    lastRound = lastStatus["last-round"]
    startRound = lastRound

    while lastRound < startRound + timeout:
        pending_txn = client.pending_transaction_info(txID)

        if pending_txn.get("confirmed-round", 0) > 0:
            return PendingTxnResponse(txID, pending_txn)

        if pending_txn["pool-error"]:
            raise Exception("Pool error: {}".format(pending_txn["pool-error"]))

        lastStatus = client.status_after_block(lastRound + 1)

        lastRound += 1

    raise Exception("Transaction {} not confirmed after {} rounds".format(txID, timeout))


def fullyCompileContract(client: AlgodClient, contract: Expr) -> bytes:
    teal = compileTeal(contract, mode=Mode.Application, version=5)
    response = client.compile(teal)
    return base64.b64decode(response["result"])


def decodeState(stateArray: List[Any]) -> Dict[bytes, Union[int, bytes]]:
    state: Dict[bytes, Union[int, bytes]] = dict()

    for pair in stateArray:
        key = base64.b64decode(pair["key"])

        value = pair["value"]
        valueType = value["type"]

        if valueType == 2:
            # value is uint64
            value = value.get("uint", 0)
        elif valueType == 1:
            # value is byte array
            value = base64.b64decode(value.get("bytes", ""))
        else:
            raise Exception(f"Unexpected state type: {valueType}")

        state[key] = value

    return state


def getAppGlobalState(client: AlgodClient, appID: int) -> Dict[bytes, Union[int, bytes]]:
    appInfo = client.application_info(appID)
    return decodeState(appInfo["params"]["global-state"])


def getBalances(client: AlgodClient, account: AlgoAccount) -> Dict[int, int]:
    balances: Dict[int, int] = dict()
    accountInfo = client.account_info(account.addr)

    # set key 0 to Algo balance
    balances[0] = accountInfo["amount"]

    assets: List[Dict[str, Any]] = accountInfo.get("assets", [])
    for assetHolding in assets:
        assetID = assetHolding["asset-id"]
        amount = assetHolding["amount"]
        balances[assetID] = amount

    return balances


def getLastBlockTimestamp(client: AlgodClient) -> Tuple[int, int]:
    status = client.status()
    lastRound = status["last-round"]
    block = client.block_info(lastRound)
    timestamp = block["block"]["ts"]

    return block, timestamp


def payAccount(
    client: AlgodClient, sender: AlgoAccount, to: AlgoAccount, amtInMicros: int
) -> PendingTxnResponse:
    """_summary_

    Args:
        client (AlgodClient): _description_
        sender (AlgoAccount): _description_
        to (AlgoAccount): _description_
        amount (int): _description_

    Returns:
        PendingTxnResponse: _description_
    """
    txn = transaction.PaymentTxn(
        sender=sender.address(),
        receiver=to.address(),
        amt=amtInMicros,
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(sender.privateSigningKey)

    try:
        txID = client.send_transaction(signedTxn)
    except:
        raise Exception(f"Failure sending transaction")
    LOGGER.info(f" ..{sender.addrShortHand} sending payment of {amtInMicros/10**6}"
                 f" algo/s to ..{to.addrShortHand} \n txID: ..{txID[-6:]}")
    try:
        r = waitForTransaction(client, signedTxn.get_txid())
    except algosdk.error.AlgodHTTPError as e:
        raise Exception(
            "Failure moving funds from dev genesis account to factory admin account \n"
            f"raised algosdk.error.AlgodHTTPError {e}"
        )
    LOGGER.info(f"Got response for ..{txID[-6:]}")
    LOGGER.debug(f"{json.dumps(r.txn, indent=4)}")
    return r
