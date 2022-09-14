import logging
from typing import Optional, List, Tuple
from random import choice
from algosdk import encoding
from algosdk.v2client.algod import AlgodClient
import algosdk.error
from algosdk.future import transaction
from algosdk.future.transaction import AssetCreateTxn, Multisig, MultisigTransaction, wait_for_confirmation, SignedTransaction
from algosdk.kmd import KMDClient
from settings import Settings
import util
from random import randint

KMD_WALLET_NAME = "unencrypted-default-wallet"
KMD_WALLET_PASSWORD = ""
FUNDING_AMOUNT = 1_000_000

kmdAccounts: Optional[List[util.AlgoAccount]] = None
LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) " "-35s %(lineno) -5d: %(message)s"
)
LOGGER = logging.getLogger(__name__)


def devFundAccount(
    settings: Settings, acctToFund: util.AlgoAccount, microAlgoAmount: int = FUNDING_AMOUNT
) -> util.PendingTxnResponse:
    """
    Raises an exception if the universe is not dev - this is only supposed to be
    used in local dev environments, not with any of the nets including testNet
    (where a faucet is required).


    Use one of the genesis accounts to fund acctToFund. This is relevant in order
    to get the new address on the dev blockchain, and also to meet the algorand
    minimum balance criteria"""

    client: AlgodClient = util.getAlgodClient(settings)
    if settings.universe != "dev":
        raise NotImplementedError(f"Only implemented for local docker dev, i.e. `dev` universe")
    fundingAccount = choice(devGetGenesisAccounts(settings))
    return util.payAccount(
        client=client, sender=fundingAccount, to=acctToFund, amtInMicros=microAlgoAmount
    )


def devGetGenesisAccounts(settings: Settings) -> List[util.AlgoAccount]:
    global kmdAccounts

    if kmdAccounts is None:
        kmd: KMDClient = util.getKMDClient(settings)

        try:
            wallets = kmd.list_wallets()
        except:
            raise Exception(
                "Algo key management demon failed to connect to chain. Check blockchain access"
            )
        walletID = None
        for wallet in wallets:
            if wallet["name"] == KMD_WALLET_NAME:
                walletID = wallet["id"]
                break

        if walletID is None:
            raise Exception("Wallet not found: {}".format(KMD_WALLET_NAME))

        walletHandle = kmd.init_wallet_handle(walletID, KMD_WALLET_PASSWORD)
        try:
            addresses = kmd.list_keys(walletHandle)
            privateKeys = [
                kmd.export_key(walletHandle, KMD_WALLET_PASSWORD, addr) for addr in addresses
            ]
            kmdAccounts = [util.AlgoAccount(sk) for sk in privateKeys]
        finally:
            kmd.release_wallet_handle(walletHandle)
        LOGGER.debug(f"Found {len(kmdAccounts)} genesis accounts in {KMD_WALLET_NAME}")
    return kmdAccounts


def createCatNFT(
    client: AlgodClient, creatorAccount: util.AlgoAccount, catPrefix: str = "GreatRed"
) -> int:
    if len(catPrefix) > 28:
        raise Exception(f"catPrefix chars must be < 28. Got {catPrefix} w {len(catPrefix)}")

    txn = transaction.AssetCreateTxn(
        sender=creatorAccount.address(),
        total=1,
        decimals=0,
        default_frozen=False,
        manager=creatorAccount.address(),
        asset_name=f"{catPrefix}Cat",
        unit_name="FancyCat",
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(creatorAccount.getPrivateSigningKey())
    client.send_transaction(signedTxn)
    response = util.waitForTransaction(client, signedTxn.get_txid())
    assert response.assetIndex is not None and response.assetIndex > 0
    print(f" GreatReadCat NFT created. assetIndex is {response.assetIndex}")
    return response.assetIndex


def createOceanAndWave() -> Tuple[util.AlgoAccount, util.AlgoAccount]:
    settings = Settings()
    oceanSk = (
        "sp4SDWmH8Rin0IhPJQq1UMsSR5C0j1IGqzLdcwCMySBVzT8lEUwjwwpS9z6l6dKSg52WWEjRdJDAL+eVt4kvBg=="
    )
    oceanAccount = util.AlgoAccount(privateKey=oceanSk)
    devFundAccount(settings, acctToFund=oceanAccount, microAlgoAmount=1_000_000)

    waveSk = (
        "FCLmrvflibLD6Deu3NNiUQCC9LOWpXLsbMR/cP2oJzH8IT4Zu8vBAhRNsXoWF+2i6q2KyBZrPhmbDCKJD7rBBg=="
    )
    waveAccount = util.AlgoAccount(privateKey=waveSk)
    devFundAccount(settings, acctToFund=waveAccount, microAlgoAmount=1_000_000)

    return [oceanAccount, waveAccount]


def createMultiSigAcct(
    oceanAccount: util.AlgoAccount, waveAccount: util.AlgoAccount, threshold: int = 1
) -> Multisig:
    if threshold not in [1, 2]:
        raise Exception(f"threshold must be 1 or 2")
    settings = Settings()
    client: AlgodClient = util.getAlgodClient(settings)
    msig = Multisig(version=1, threshold=threshold, addresses=[oceanAccount.addr, waveAccount.addr])

    # Fund the multisig account from a genesis account
    gen = devGetGenesisAccounts(settings)[0]
    txn = transaction.PaymentTxn(
        sender=gen.addr, receiver=msig.address(), amt=500_000, sp=client.suggested_params()
    )
    signedTxn = txn.sign(gen.sk)
    client.send_transaction(signedTxn)
    return msig


def sendSignedMtx(mtx: MultisigTransaction, subAcct: util.AlgoAccount) -> int:
    # Sending signed transaction
    settings = Settings()
    client: AlgodClient = util.getAlgodClient(settings)
    txid = client.send_raw_transaction(
        encoding.msgpack_encode(mtx)) 
    print("Sent. Waiting for confirmation")
    confirmed_txn = wait_for_confirmation(client, txid, 6)
    nftID = confirmed_txn['asset-index']
    print(nftID)
    return nftID


def makeSignAndReturnNftCreationMtx(
        msig: Multisig, 
        subAcct: util.AlgoAccount
        ) -> Tuple[AssetCreateTxn, MultisigTransaction]:
    """ 
    Makes a transaction for creating an NFT by multisig,
    signs with the subaccount, returns unsigned transaction and
    signed but unsent MultisigTransaction""" 
    
    settings = Settings()
    client: AlgodClient = util.getAlgodClient(settings)
    randomNumber = randint(0, 999)
    randomNote = bytes(randint(0, 255) for _ in range(20))
    txn = transaction.AssetCreateTxn(
            sender=msig.address(),
            total=1,
            decimals=0,
            default_frozen=False,
            manager=msig.address(),
            asset_name=f"SeaWave{randomNumber}",
            unit_name=f"W{randomNumber}",
            note=randomNote,
            sp=client.suggested_params(),
    )
    mtx = MultisigTransaction(txn, msig)
    mtx.sign(subAcct.sk)
    return [txn, mtx]


def makeSignAndReturnNftCreationSingle(
        acct: util.AlgoAccount
        ) -> Tuple[AssetCreateTxn, SignedTransaction]:
    """ 
    Makes a signed transaction for creating an NFT with a single account,
    and returns the txn before sig and also the SignedTransaction"""

    settings = Settings()
    client: AlgodClient = util.getAlgodClient(settings)
    randomNumber = randint(0, 999)
    randomNote = bytes(randint(0, 255) for _ in range(20))
    txn = transaction.AssetCreateTxn(
            sender=acct.address(),
            total=1,
            decimals=0,
            default_frozen=False,
            manager=acct.address(),
            asset_name=f"SeaWave{randomNumber}",
            unit_name=f"W{randomNumber}",
            note=randomNote,
            sp=client.suggested_params(),
    )
    stx = txn.sign(acct.sk)
    return txn, stx


def multiMakesNft(
        msig: Multisig, 
        subAcct: util.AlgoAccount
        ) -> Tuple[bool, AssetCreateTxn, MultisigTransaction]:
    """multisig account makes an NFT
    Returns:
        Tuple[bool, AssetCreateTxn, MultisigTransaction]: bool True if 
        asset was created, False if AlgoHTTPError thrown. Also
        returns the transaction and the multsig signed mtx
    """
    txn, mtx = makeSignAndReturnNftCreationMtx(msig, subAcct)
    try:
        sendSignedMtx(mtx, subAcct)
    except algosdk.error.AlgodHTTPError as e: 
        print(f"AlgoHTTPError: {e}")
        print(mtx.multisig.json_dictify())
        return False, txn, mtx
    print("success sending")
    print(mtx.multisig.json_dictify())
    return True, txn, mtx


def singleMakesNft(acct: util.AlgoAccount) -> Tuple[AssetCreateTxn, SignedTransaction]:
    """regular singal sign account makes an NFT
    Returns:
        Tuple[bool, AssetCreateTxn, SignedTransaction]: bool True if 
        asset was created, False if AlgoHTTPError thrown. Also
        returns the transaction and the multsig signed mtx
    """
    txn, stx = makeSignAndReturnNftCreationSingle(acct)
    try:
        sendSignedMtx(stx, acct)
    except algosdk.error.AlgodHTTPError as e: 
        print(f"AlgoHTTPError: {e}")
        print(f"Signature {stx.signature}")
        return False, txn, stx
    print("success sending")
    print(f"Signature {stx.signature}")
    return True, txn, stx