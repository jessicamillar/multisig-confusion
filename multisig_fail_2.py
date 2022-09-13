"""
Run ./sandbox reset first
5 NFTs made by ocean (first in msig signers list)
"""

from settings import Settings
import logging
import dev_setup
import util
from algosdk.v2client.algod import AlgodClient

logging.basicConfig(level='DEBUG')


oceanAccount, waveAccount = dev_setup.createOceanAndWave()
msig = dev_setup.createMultiSigAcct(
    oceanAccount=oceanAccount,
    waveAccount=waveAccount,
    threshold=1)

settings = Settings()
client: AlgodClient = util.getAlgodClient(settings)

print("##############################")
print("Now for sample single signing")

n = 5
for i in range(n):
    i +=1
    print(f"Making nft signed by wave ({i} of {n})")
    dev_setup.multiMakesNft(msig=msig, subAcct=oceanAccount)


