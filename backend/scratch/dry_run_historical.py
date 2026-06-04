import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from src.utils.db import getConn
from src.utils.rollupscoperepository import (
    listScopeTx,
    resolveRequiredSourceAtomicIdsTx
)
from src.utils.rollupbatchrepository import (
    getBatch,
)

def run():
    print("Running historical dry run...")
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT id FROM ESG_ROLLUP_BATCH WHERE delete_yn = 0 ORDER BY id DESC LIMIT 5")
            batches = cur.fetchall()
            for b in batches:
                batchId = b["id"]
                print(f"Batch {batchId}:")
                scopes = listScopeTx(cur, batchId)
                print(f"  Scopes count: {len(scopes)}")
                reqSrc = resolveRequiredSourceAtomicIdsTx(cur, batchId)
                print(f"  Required Source IDs: {len(reqSrc)}")
                
    finally:
        conn.close()
    print("Done")

if __name__ == "__main__":
    run()
