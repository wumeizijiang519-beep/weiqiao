"""Determinism and contract tests for support-gradient banks."""
import numpy as np
from candidate_bank import build_bank
def main():
 rng=np.random.default_rng(202643001); native=rng.normal(size=(4,32,7)).astype(np.float32); native[:,:,6]=np.where(rng.random((4,32))>.5,1,-1); scale=np.ones(7,dtype=np.float32); offset=np.zeros(7,dtype=np.float32); raw=native.copy(); basis=np.zeros((3,32,6),dtype=np.float32)
 first=build_bank(native,raw,scale,offset,basis,.25,.5); second=build_bank(native,raw,scale,offset,basis,.25,.5)
 assert np.array_equal(first['native'],second['native']); assert first['hashes']==second['hashes']; assert first['native'].shape==(8,32,7); assert np.array_equal(first['native'][4:,:,6],np.broadcast_to(native[0,:,6],(4,32))); print('SUPPORT_GRADIENT_BANK_TEST_PASS')
if __name__=='__main__': main()
