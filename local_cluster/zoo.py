from kazoo.client import KazooClient
import subprocess

ip = (
    subprocess.run(["uvt-kvm", "ip", "ch1"], capture_output=True)
    .stdout.strip()
    .decode()
)


def tree(zk, path, indent=""):
    print(path, b" ".join(s for s in zk.get(path)[0].split() if s))
    for p in zk.get_children(path):
        tree(zk, path + "/" + p, indent + "\t")


zk = KazooClient(hosts=f"{ip}:9181")
zk.start()

tree(zk, "/")
# print(zk.get_children("/clickhouse/tables/table1"))
# print(zk.get("/clickhouse/tables/table1"))
