# INSTALL
# pip3 install chevron paramiko

# wget https://github.com/ClickHouse/ClickHouse/releases/download/v22.8.4.7-lts/clickhouse-common-static-22.8.4.7-amd64.tgz
# tar xvf clickhouse-common-static-22.8.4.7-amd64.tgz
# mv clickhouse-common-static-22.8.4.7/usr/bin/clickhouse .
# rm clickhouse-common-static-22.8.4.7-amd64.tgz
# rm -rf clickhouse-common-static-22.8.4.7

# sudo apt install uvtool
# uvt-simplestreams-libvirt sync release=focal arch=amd64
# uvt-kvm create ch1 release=focal
# uvt-kvm create ch2 release=focal
#
# TEST RESULT
# clickhouse client --host $(uvt-kvm ip ch1) --multiquery < create.sql

import chevron
import paramiko
import subprocess
from time import sleep

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.load_system_host_keys()

cluster = [
    {
        "shard": f"{i//2+1:02d}",
        "replica": f"{i%2+1:02d}",
        "hostname": f"ch{i+1}",
        "idx": i + 1,
    }
    for i in range(2)
]
from pprint import pprint

pprint(cluster)

for c in cluster:
    c["ip"] = (
        subprocess.run(["uvt-kvm", "ip", c["hostname"]], capture_output=True)
        .stdout.strip()
        .decode()
    )


def run_command(ssh, command):
    """Executes command via SSH."""
    stdin, stdout, stderr = ssh.exec_command(command)
    stdin.flush()
    stdin.channel.shutdown_write()
    ret = stdout.read()
    err = stderr.read()
    if ret:
        return ret
    elif err:
        raise RuntimeError(err)
    else:
        return None


for c in cluster:
    print(f'stopping {c["hostname"] }')
    ssh.connect(c["ip"], username="ubuntu")
    ssh.exec_command("pkill clickhouse")
    ssh.close()

sleep(5)

for c in cluster:
    print(f'stopping -9 {c["hostname"] }')
    ssh.connect(c["ip"], username="ubuntu")
    ssh.exec_command("pkill -9 clickhouse")
    ssh.close()

sleep(5)

for c in cluster:
    print(f'cleaning {c["hostname"] }')
    ssh.connect(c["ip"], username="ubuntu")
    run_command(ssh, "rm -rf chdir*")
    run_command(ssh, "rm -rf keeper*")
    run_command(ssh, "rm -rf state")
    ssh.close()

for c in cluster:
    print(f'setting hosts on {c["hostname"] }')
    ssh.connect(c["ip"], username="ubuntu")

    for c2 in cluster:
        if c is not c2:
            print(
                f'echo "{c2["ip"]} {c2["hostname"]} {c2["hostname"]}" | sudo tee -a /etc/hosts'
            )
            print(
                run_command(
                    ssh,
                    f'echo "{c2["ip"]} {c2["hostname"]} {c2["hostname"]}" | sudo tee -a /etc/hosts',
                )
            )
    ssh.close()


for c in cluster:
    print(f'configuring {c["hostname"] }')

    ssh.connect(c["ip"], username="ubuntu")
    ftp = ssh.open_sftp()
    file = ftp.file("config.xml", "w", -1)
    file.write(
        chevron.render(
            open("config_template.xml").read(),
            {
                "cluster": cluster,
                **c,
            },
        )
    )
    file.flush()
    ftp.close()

    subprocess.run(["scp", "clickhouse", "ubuntu@" + c["ip"] + ":"])
    subprocess.run(["scp", "users.xml", "ubuntu@" + c["ip"] + ":"])

    ssh.exec_command("chmod +x clickhouse")

    ssh.exec_command("nohup ./clickhouse server &")
    ssh.close()
