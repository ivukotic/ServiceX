import time
import codecs
import redis

import pyarrow as pa
# import awkward
import requests

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


r = redis.Redis(host='redis.slateci.net', port=6379, db=0)
sx_host = "https://servicex.slateci.net"
req_id = "g3xJJWwBMWltPFRMX2Yn"
group = "my_group"

sInfo = None
try:
    sInfo = r.xinfo_groups(req_id)
    print('stream group info:', sInfo)
except Exception as rex:
    print("stream info exception: ", rex)


if not sInfo:
    print("creating stream group")
    r.xgroup_create(req_id, group, '0', mkstream=True)

# sInfo = r.xinfo_groups(req_id)
# print(sInfo)
print('start fetching data...')
tot_processed = 0
while True:
    a = r.xreadgroup(group, 'Alice', {req_id: '>'}, count=1, block=None, noack=False)
    if not a:
        # print("Done.")
        time.sleep(.5)
        # break
        continue

    # print(a[0][1][0])
    mid = a[0][1][0][0]
    # print(mid)
    mess = a[0][1][0][1]
    # print(mess)
    evid = a[0][1][0][1][b'pa']
    data = a[0][1][0][1][b'data']
    print(evid)
    # print(data)
    adata = codecs.decode(data, 'bz2')

    reader = pa.ipc.open_stream(adata)
    batches = [b for b in reader]
    batch = batches[0]
    # print(batch.schema)
    # print(batch[1])
    requests.put(sx_host + "/drequest/events_processed/" + req_id + "/" + str(batch.num_rows), verify=False)
    tot_processed += batch.num_rows
    print('cols:', batch.num_columns, 'rows:', batch.num_rows, 'processed:', tot_processed)
    r.xack(req_id, group, mid)
    r.xdel(req_id, mid)

print('consumers:', r.xinfo_consumers(req_id, group))
print('pending:', r.xpending(req_id, group))
# print(r.get('foo'))