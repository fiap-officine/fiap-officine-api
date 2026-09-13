import os
import sys
import json
import base64

def setup_kubeconfig():
    raw = os.environ.get("KUBE_CONFIG_RAW", "").strip()
    if not raw:
        print("Warning: KUBE_CONFIG_RAW is empty.")
        return

    # 1. Se estiver envolvido em aspas JSON ou literais
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = raw[1:-1]
        raw = raw.strip()

    # 2. Tenta decodificar de Base64 se a decodificacao contiver apiVersion/clusters
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        if "apiVersion" in decoded or "clusters" in decoded:
            raw = decoded.strip()
    except Exception:
        pass

    # 3. Se quebras de linha vieram escapadas como \n literal
    if "\\n" in raw:
        raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n")

    # 4. Remove possíveis aspas extras residuais
    raw = raw.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()

    target = os.path.expanduser("~/.kube/config")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(raw.strip() + "\n")

    print(f"Kubeconfig configurado com sucesso em {target} ({len(raw)} bytes).")

if __name__ == "__main__":
    setup_kubeconfig()
