"""Use the unmodified ComfyUI HTTP/WebSocket APIs and benchmark native GPU VRAM."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import statistics
import threading
import time
import uuid
from urllib.parse import urlencode

import requests
from PIL import Image, ImageStat
import websocket

WORKFLOWS = Path(__file__).parent / "workflows"


def configure(graph, prompt=None, seed=None, width=1024, height=1024, image=None):
    if any(value < 16 or value % 16 for value in (width, height)):
        raise ValueError("Width and height must be positive multiples of 16")
    result = copy.deepcopy(graph)
    if prompt is not None:
        result["4"]["inputs"]["text"] = prompt
    if seed is not None:
        if not 0 <= seed < 2**64:
            raise ValueError("Seed must be an unsigned 64-bit integer")
        result["6"]["inputs"]["noise_seed"] = seed
    for node in ("5", "8"):
        result[node]["inputs"].update(width=width, height=height)
    if image is not None:
        result["14"]["inputs"]["image"] = image
    return result


def ui_workflow(graph, schemas):
    """Produce standard editable workflow metadata using the server's node schemas."""
    nodes, links = {}, []
    for index, (key, node) in enumerate(graph.items()):
        schema = schemas[node["class_type"]]
        widgets = []
        for group in ("required", "optional"):
            for name, spec in schema["input"].get(group, {}).items():
                value = node["inputs"].get(name)
                if value is None or isinstance(value, list):
                    continue
                widgets.append(value)
                if len(spec) > 1 and isinstance(spec[1], dict) and spec[1].get("control_after_generate"):
                    widgets.append("fixed")
        nodes[key] = {
            "id": int(key), "type": node["class_type"],
            "title": node.get("_meta", {}).get("title", node["class_type"]),
            "pos": [(index % 4) * 360, (index // 4) * 300], "size": [320, 230],
            "flags": {}, "order": index, "mode": 0, "inputs": [],
            "outputs": [{"name": name, "type": kind, "links": []}
                        for name, kind in zip(schema.get("output_name", schema["output"]), schema["output"])],
            "properties": {"Node name for S&R": node["class_type"]},
            "widgets_values": widgets,
        }
    for key, node in graph.items():
        schema = schemas[node["class_type"]]
        specs = schema["input"].get("required", {}) | schema["input"].get("optional", {})
        for name, value in node["inputs"].items():
            if not isinstance(value, list):
                continue
            origin, slot = value
            link_id = len(links) + 1
            target_slot = len(nodes[key]["inputs"])
            kind = schemas[graph[origin]["class_type"]]["output"][slot]
            entry = {"name": name, "type": kind, "link": link_id}
            if specs[name][0] in ("INT", "FLOAT", "STRING", "BOOLEAN"):
                entry["widget"] = {"name": name}
            nodes[key]["inputs"].append(entry)
            nodes[origin]["outputs"][slot]["links"].append(link_id)
            links.append([link_id, int(origin), slot, int(key), target_slot, kind])
    return {"version": 0.4, "last_node_id": max(map(int, nodes)), "last_link_id": len(links),
            "nodes": list(nodes.values()), "links": links, "groups": [], "config": {}, "extra": {}}


class VramSampler:
    """Whole-device VRAM sampled from amdgpu; includes desktop/other processes."""
    def __init__(self):
        self.path = Path("/sys/class/drm/renderD128/device/mem_info_vram_used")
        self.stop = threading.Event()
        self.values = []

    def sample(self):
        while not self.stop.is_set():
            self.values.append(int(self.path.read_text()))
            self.stop.wait(0.02)

    def __enter__(self):
        self.baseline = int(self.path.read_text())
        self.values.append(self.baseline)
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join()

    def report(self):
        return {"baseline_bytes": self.baseline, "sampled_peak_bytes": max(self.values),
                "peak_above_baseline_bytes": max(self.values) - self.baseline,
                "samples": len(self.values), "sample_interval_ms": 20,
                "scope": "whole GPU including desktop; sampled, not PyTorch allocator peak"}


class Client:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.http = requests.Session()
        self.http.trust_env = False
        self.schemas = self.get("/object_info")

    def get(self, route):
        response = self.http.get(self.url + route, timeout=30)
        response.raise_for_status()
        return response.json()

    def upload(self, path):
        with path.open("rb") as file:
            response = self.http.post(self.url + "/upload/image", files={"image": (path.name, file, "image/png")},
                                      data={"type": "input", "overwrite": "false"}, timeout=60)
        response.raise_for_status()
        data = response.json()
        return "/".join(filter(None, (data.get("subfolder"), data["name"])))

    def generate(self, graph, output, label):
        queue = self.get("/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI queue is busy; benchmark requires an idle queue")
        client_id = str(uuid.uuid4())
        ws_url = self.url.replace("https://", "wss://").replace("http://", "ws://")
        ws = websocket.create_connection(ws_url + "/ws?" + urlencode({"clientId": client_id}), timeout=30)
        workflow = ui_workflow(graph, self.schemas)
        payload = {"prompt": graph, "client_id": client_id,
                   "extra_data": {"extra_pnginfo": {"workflow": workflow}}}
        output.mkdir(parents=True, exist_ok=True)
        (output / f"{label}-api.json").write_text(json.dumps(graph, indent=2) + "\n")
        (output / f"{label}-ui.json").write_text(json.dumps(workflow, indent=2) + "\n")
        with VramSampler() as vram:
            started = time.monotonic()
            response = self.http.post(self.url + "/prompt", json=payload, timeout=30)
            if not response.ok:
                raise RuntimeError(f"Workflow rejected: {response.status_code} {response.text}")
            data = response.json()
            if data.get("node_errors"):
                raise RuntimeError(f"Invalid nodes: {data['node_errors']}")
            prompt_id = data["prompt_id"]
            events = []
            deadline = started + 1800
            try:
                while time.monotonic() < deadline:
                    try:
                        raw = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if isinstance(raw, bytes):
                        continue
                    if not raw:
                        raise RuntimeError("ComfyUI closed the WebSocket during generation")
                    event = json.loads(raw)
                    if event.get("data", {}).get("prompt_id") != prompt_id:
                        continue
                    events.append(event)
                    if event["type"] in ("execution_error", "execution_interrupted"):
                        raise RuntimeError(json.dumps(event))
                    if event["type"] == "executing" and event["data"]["node"] is None:
                        break
                else:
                    raise TimeoutError(f"Generation timed out; prompt {prompt_id} may still be running")
            finally:
                ws.close()
            elapsed = time.monotonic() - started
        history = self.get(f"/history/{prompt_id}")[prompt_id]
        if history["status"]["status_str"] != "success":
            raise RuntimeError(json.dumps(history["status"]))
        files = []
        for node_output in history["outputs"].values():
            for item in node_output.get("images", []):
                response = self.http.get(self.url + "/view", params=item, timeout=60)
                response.raise_for_status()
                png = Image.open(io.BytesIO(response.content))
                if png.format != "PNG" or png.size != (graph["5"]["inputs"]["width"], graph["5"]["inputs"]["height"]):
                    raise RuntimeError("Unexpected output format or dimensions")
                saved_graph = json.loads(png.info["prompt"])
                # ComfyUI adds input-file fingerprints to nodes during execution.
                # Compare the submitted graph without those server cache fields.
                for key, node in saved_graph.items():
                    if "is_changed" not in graph.get(key, {}):
                        node.pop("is_changed", None)
                if saved_graph != graph or json.loads(png.info["workflow"]) != workflow:
                    raise RuntimeError("Output PNG workflow metadata did not round-trip")
                if max(ImageStat.Stat(png.convert("RGB")).stddev) < 1:
                    raise RuntimeError("Generated output is nearly uniform")
                path = output / f"{label}-{len(files)}.png"
                path.write_bytes(response.content)
                files.append({"path": str(path), "server": item,
                              "sha256": hashlib.sha256(response.content).hexdigest()})
        if not files:
            raise RuntimeError("No PNG outputs returned")
        (output / f"{label}-history.json").write_text(json.dumps(history, indent=2) + "\n")
        record = {"label": label, "prompt_id": prompt_id, "seconds": elapsed,
                  "vram": vram.report(), "files": files, "events": events}
        print(f"{label}: {elapsed:.3f}s; sampled GPU peak {max(vram.values) / 1024**3:.3f} GiB", flush=True)
        return record


def benchmark(client, output, seed):
    output = output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "url": client.url,
              "system_stats": client.get("/system_stats"), "runs": []}
    output.mkdir(parents=True)
    for kind, seed in (("text-to-image", seed), ("reference-edit", seed + 100)):
        graph = json.loads((WORKFLOWS / f"{kind}-api.json").read_text())
        image = None
        if kind == "reference-edit":
            image = client.upload(Path(report["runs"][0]["files"][0]["path"]))
        for index in range(3):
            configured = configure(graph, seed=seed + index, image=image)
            record = client.generate(configured, output, f"{kind}-{'first' if index == 0 else 'warm-' + str(index)}")
            report["runs"].append(record)
            (output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    report["warm_median_seconds"] = {
        kind: statistics.median(run["seconds"] for run in report["runs"] if run["label"].startswith(kind + "-warm"))
        for kind in ("text-to-image", "reference-edit")}
    (output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Results: {output / 'benchmark.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["benchmark", "generate"])
    parser.add_argument("--url", default="http://127.0.0.1:8188")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow", choices=["text-to-image", "reference-edit"], default="text-to-image")
    parser.add_argument("--prompt")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    client = Client(args.url)
    if args.action == "benchmark":
        benchmark(client, args.output, args.seed)
    else:
        graph = json.loads((WORKFLOWS / f"{args.workflow}-api.json").read_text())
        if args.workflow == "reference-edit" and args.image is None:
            parser.error("reference-edit requires --image")
        image = client.upload(args.image) if args.image else None
        graph = configure(graph, args.prompt, args.seed, args.width, args.height, image)
        result = client.generate(graph, args.output, "generated")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
