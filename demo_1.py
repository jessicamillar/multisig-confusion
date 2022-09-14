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
print("Now for sample single signing")
print("")


print(f"mtx1: signed NFT create transaction signed by ocean")
success1, txn1, mtx1 = dev_setup.multiMakesNft(msig=msig, subAcct=oceanAccount)

print(f"mtx2: signed NFT create transaction signed by wave")
success2, txn2, mtx2 = dev_setup.multiMakesNft(msig=msig, subAcct=waveAccount)

if not success2:
    print("..")
    time.sleep(2)
    print("")
    print("##############################")
    print("THIS FAILED. Note above the MultiSigTransaction mtx2 inherited the old wave sig from mtx1!!")
    print(f"Even though:")
    print(f"txn1.note == txn2.note: {txn1.note == txn2.note}")
    print(f"txn1.asset_name == txn2.asset_name: {txn1.asset_name == txn2.asset_name}")
    print(f"txn1.unit_name == txn2.unit_name: {txn1.unit_name == txn2.unit_name}")

assert (success1 and not success2)
assert txn1.note != txn2.note
assert txn1.asset_name != txn2.asset_name
assert txn1.unit_name != txn2.unit_name

time.sleep(8)
print("")
print("##############################")
print(f"Now generate the same pattern of NFT, except with a single sign account.")


# Now generate the same pattern of NFT, except with a single sign account
success3, txn3, stx3 = dev_setup.singleMakesNft(acct=oceanAccount)
success4, txn4, stx4 = dev_setup.singleMakesNft(acct=waveAccount)

if success3 and success4:
    print("Both of these succeeded")