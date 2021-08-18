# import plyvel
# dir_path = os.path.dirname(os.path.realpath(__file__))
# print(dir_path)
# db = plyvel.DB('/dev/shm/test_leveldb', create_if_missing=True)
# db.put(b'key', b'value')
# db.put(b'another-key', b'another-value')
# for key, value in db:
#     print(key,value)

import leveldb
xx="leveldb"
db = leveldb.DB(f"/dev/shm/{xx}".encode('utf-8'), create_if_missing=True)
healthdict = {
    "health-check.cpu-load.cpu-load-total.total-cpu-percent": "10",
    "health-check.network-connections.network-connections-total.receive-total-rate": "100"
}
db.put(b"health-check.keys", ';'.join(list(healthdict.keys())).encode('utf-8'))
for k, v in healthdict.items():
    db.put(k.encode('utf-8'), v.encode('utf-8'))

for key, value in db:
    print(f"the key is :{key.decode('utf-8')} ----->  value is : {value.decode('utf-8')}")

monitor_keys = db.get(b'health-check.keys').decode('utf-8').split(';')
print(f"monitor_keys is ------> {monitor_keys}")

db.close()