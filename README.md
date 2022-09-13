WANT:
Multisig with two signers, where either one can sign any transaction


ISSUE: it seems that the single signature typically works once and then sporadically. 

multisig_fail_1.py through multisig_fail_3.py give different failure examples. The failure condition is:

`algosdk.error.AlgodHTTPError: At least one signature didn't pass verification`

Also included is a jupyter notebook jupyter_multisig_fail.ipynb


The code expects to be running with local sandbox, where you reset it 
in between failures. I.e. in sandbox repo:

`./sandbox reset`

If you don't reset, you will keep adding dollars to the accounts.