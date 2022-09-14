"""
Run ./sandbox reset first
5 NFTs made by wave (second in msig signers list)
"""
import time
from settings import Settings
import logging
import dev_setup
import util
from algosdk.v2client.algod import AlgodClient

logging.basicConfig(level='INFO')

print(f"Fund ocean, fund wave, fund [ocean,wave] joint acct")

oceanAccount, waveAccount = dev_setup.createOceanAndWave()
msig = dev_setup.createMultiSigAcct(
    oceanAccount=oceanAccount,
    waveAccount=waveAccount,
    threshold=1)


settings = Settings()
client: AlgodClient = util.getAlgodClient(settings)



print("")
print("##############################")
print("Now for sample single signing - all signatures by ociean")
print("")


idx = 0
success, txn, mtx = dev_setup.multiMakesNft(msig=msig, subAcct=oceanAccount)

while success:
    success, new_txn, new_mtx = dev_setup.multiMakesNft(msig=msig, subAcct=oceanAccount)
    idx += 1
    if success is True:
        txn = new_txn,
        mtx = new_mtx
    if idx > 10:
        success = False


print("")
print("")
print("Last successful ")