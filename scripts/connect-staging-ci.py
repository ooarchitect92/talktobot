"""Connect a hosted deployment job to staging without exposing the EKS endpoint."""
import base64
import json
import os
import socket
import subprocess
import time
from pathlib import Path


def aws(*arguments):
    return json.loads(subprocess.check_output(["aws", "--region", "ap-south-1", *arguments, "--output", "json"]))


def main():
    if aws("sts", "get-caller-identity")["Account"] != "510439383733":
        raise RuntimeError("Unexpected staging account")
    cluster = aws("eks", "describe-cluster", "--name", "talktobot-staging")["cluster"]
    if cluster["resourcesVpcConfig"]["endpointPublicAccess"] or cluster["status"] != "ACTIVE":
        raise RuntimeError("Expected active private staging cluster")
    nodes = aws("ec2", "describe-instances", "--filters", "Name=tag:eks:cluster-name,Values=talktobot-staging",
                "Name=instance-state-name,Values=running")
    candidates = {n["InstanceId"] for r in nodes["Reservations"] for n in r["Instances"]
                  if n["VpcId"] == cluster["resourcesVpcConfig"]["vpcId"]}
    managed = aws("ssm", "describe-instance-information")["InstanceInformationList"]
    target = next(n["InstanceId"] for n in managed if n["InstanceId"] in candidates and n["PingStatus"] == "Online")
    directory = Path(os.environ["RUNNER_TEMP"]) / "kube"
    directory.mkdir(mode=0o700, exist_ok=True)
    ca = directory / "ca.crt"
    ca.write_bytes(base64.b64decode(cluster["certificateAuthority"]["data"]))
    subprocess.run(["kubectl", "config", "set-cluster", "arn:aws:eks:ap-south-1:510439383733:cluster/talktobot-staging",
                    "--server=https://127.0.0.1:9443", "--tls-server-name=" + cluster["endpoint"].removeprefix("https://"),
                    "--certificate-authority=" + str(ca), "--embed-certs=true"], check=True)
    with (directory / "tunnel.log").open("wb") as log:
        process = subprocess.Popen(["aws", "ssm", "start-session", "--region", "ap-south-1", "--target", target,
                                    "--document-name", "talktobot-staging-eks-tunnel"], stdout=log, stderr=log,
                                   start_new_session=True)
    (directory / "tunnel.pid").write_text(str(process.pid))
    for _ in range(60):
        if process.poll() is not None:
            message = (directory / "tunnel.log").read_text(errors="replace")
            reason = "AWS session permission denied" if "AccessDenied" in message or "not authorized" in message else "session transport failed"
            raise RuntimeError(f"Private staging tunnel exited: {reason}")
        try:
            with socket.create_connection(("127.0.0.1", 9443), timeout=1):
                break
        except OSError:
            time.sleep(1)
    else:
        process.terminate()
        raise RuntimeError("Private staging tunnel did not become ready")
    subprocess.run(["kubectl", "get", "serviceaccounts", "--namespace", "northstar"], check=True)
    print("Private staging connection established with original CA and hostname verification.")


if __name__ == "__main__":
    main()
