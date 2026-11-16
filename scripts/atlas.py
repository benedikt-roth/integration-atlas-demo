#!/usr/bin/env python3
"""Load per-entity JSON, validate with CUE, and render repository Markdown."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {"systems": "systems", "components": "components", "interfaces": "interfaces",
           "dataContracts": "data-contracts", "views": "views"}
KINDS = {"system": "systems", "component": "components", "interface": "interfaces",
         "dataContract": "data-contracts", "view": "views"}
IGNORED = {".git", ".venv", ".build", "__pycache__", "node_modules"}


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{path}: duplicate JSON key {key!r}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def output_path(kind, identifier):
    return f"docs/generated/{KINDS[kind]}/{identifier}.md"


def load_model(root):
    """I/O only: CUE owns the entity schemas and cross-reference policies."""
    model = {}
    for collection, folder in FOLDERS.items():
        model[collection] = {}
        for path in sorted((root / "model" / folder).glob("*.json")):
            if path.is_symlink():
                raise ValueError(f"Entity files must not be symlinks: {path}")
            identifier, separator, name = path.stem.partition("--")
            if not separator or not name:
                raise ValueError(f"Use ID--descriptive-name.json: {path}")
            if identifier in model[collection]:
                raise ValueError(f"Duplicate entity file ID: {identifier}")
            model[collection][identifier] = read_json(path)
    files = {}
    for directory, children, names in os.walk(root):
        children[:] = sorted(n for n in children if n not in IGNORED and not (Path(directory) / n).is_symlink())
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            facts = {}
            if relative.startswith("contracts/"):
                if path.suffix == ".xsd":
                    schema = ET.parse(path).getroot()
                    if schema.tag != "{http://www.w3.org/2001/XMLSchema}schema":
                        raise ValueError(f"Not an XSD schema: {relative}")
                    if schema.get("version") is not None:
                        facts["version"] = schema.get("version")
                elif path.suffix == ".json":
                    data = read_json(path)
                    if isinstance(data, dict) and "openapi" in data:
                        facts["version"] = data.get("info", {}).get("version", "")
            files[relative] = facts
    # Canonical entity links may target pages produced by this build.
    for kind, folder in KINDS.items():
        collection = next(k for k, v in FOLDERS.items() if v == folder)
        for identifier in model[collection]:
            files[output_path(kind, identifier)] = {}
    files["docs/generated/index.md"] = {}
    model["files"] = files
    return model


def validate(root):
    binary = os.environ.get("CUE", "cue")
    if not shutil.which(binary):
        raise ValueError("CUE is required. Install CUE v0.17.1 or set CUE=/path/to/cue; see README.md.")
    build = root / ".build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build) as directory:
        source = Path(directory) / "input.json"
        source.write_text(json.dumps(load_model(root)), encoding="utf-8")
        result = subprocess.run([binary, "export", str(root / "schemas/model.cue"), str(source),
                                 "-d", "#Model", "--out", "json"], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError("CUE validation failed:\n" + result.stderr.strip())
    model = json.loads(result.stdout)
    model.pop("files")
    return model


def md_text(value):
    return html.escape(str(value), quote=False).replace("\\", "\\\\").replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("\n", " ")


def flow_text(value):
    # Mermaid entities survive GitHub's HTML preprocessing without becoming syntax.
    escapes = {'"': '#34;', "'": '#39;', '<': '#60;', '>': '#62;', '|': '#124;',
               ';': '#59;', '#': '#35;', '&': '#38;', '\n': ' ', '\r': ' '}
    return "".join(escapes.get(c, c) for c in str(value))


def relative_link(label, target, page):
    relative = Path(os.path.relpath(target, Path(page).parent)).as_posix()
    return f"[{md_text(label)}]({quote(relative, safe='/.-_~')})"


def github_url(context, path):
    return f"https://github.com/{context['repository']}/blob/{quote(context['ref'], safe='/-._~')}/{quote(path, safe='/-._~')}"


def entity(model, reference):
    return model[FOLDERS_KEY(reference["kind"])][reference["id"]]


def FOLDERS_KEY(kind):
    return next(k for k, v in FOLDERS.items() if v == KINDS[kind])


def target_path(target):
    return target["path"] if target["kind"] == "file" else output_path(target["kind"], target["id"])


def scenario(model, view):
    """Resolve validated usages into physical hops; never infer an interface by direction."""
    messages, requests = [], {}
    for number, step in enumerate(view["steps"], 1):
        original = requests[step["responseTo"]][0] if step["kind"] == "response" else step
        response_number = requests[step["responseTo"]][1] if step["kind"] == "response" else None
        if step["kind"] != "response":
            requests[step["id"]] = (step, number)
        owner = model["interfaces"][original["interface"]["id"]]["owner"]
        sender, receiver = original["participant"], owner
        if original["kind"] == "event":
            sender, receiver = receiver, sender
        route = original.get("transport")
        if route:
            router = model["interfaces"][route["viaInterface"]["id"]]["owner"]
            hops = [(sender, router, route["viaInterface"], True),
                    (router, receiver, original["interface"], route["envelopeScope"] == "end-to-end")]
        else:
            hops = [(sender, receiver, original["interface"], False)]
        if step["kind"] == "response":
            hops = [(b, a, contract, envelope) for a, b, contract, envelope in reversed(hops)]
        for index, (source, target, contract, carries_envelope) in enumerate(hops):
            label = str(number) + (chr(97 + index) if len(hops) > 1 else "")
            messages.append({"number": label, "logicalNumber": number, "stepId": step["id"],
                             "kind": step["kind"], "responseTo": response_number,
                             "source": source, "target": target, "interface": contract,
                             "payload": original["interface"], "transport": route,
                             "envelope": route["envelope"] if carries_envelope else None,
                             "annotation": step["annotation"], "viewId": view["id"]})
    return messages


def message_links(model, message):
    interface = message["interface"]
    links = [(f"{interface['id']} v{interface['version']}", output_path("interface", interface["id"]))]
    links.extend((a["label"], a["path"]) for a in model["interfaces"][interface["id"]]["versions"][interface["version"]]["artifacts"])
    if message["envelope"]:
        envelope = message["envelope"]
        links.append((f"{envelope['id']} v{envelope['version']}", output_path("dataContract", envelope["id"])))
        links.extend((a["label"], a["path"]) for a in model["dataContracts"][envelope["id"]]["versions"][envelope["version"]]["artifacts"])
    links.extend((a["label"], target_path(a["target"])) for a in message["annotation"]["links"])
    # Explicit annotation labels override automatic labels for the same destination.
    return list({path: (label, path) for label, path in links}.values())


def flowchart(model, messages, context, overview=False):
    references = {r["id"]: r for m in messages for r in (m["source"], m["target"])}
    nodes = {identifier: f"N{n}" for n, identifier in enumerate(sorted(references))}
    lines = ["flowchart LR"]
    for identifier, reference in sorted(references.items()):
        name = entity(model, reference)["name"]
        lines.append(f'  {nodes[identifier]}["{flow_text(name)}"]')
    for message in messages:
        prefix = "" if overview else message["number"] + ". "
        contract = message["interface"]
        label = prefix + flow_text(message["annotation"]["text"])
        label += f"<br/>{contract['id']} v{flow_text(contract['version'])}"
        if message["envelope"]:
            env = message["envelope"]
            label += f"<br/>Envelope {env['id']} v{flow_text(env['version'])}"
        if message["responseTo"]:
            label += f"<br/>Response to step {message['responseTo']}"
        anchors = [f"<a href='{html.escape(github_url(context, path), quote=True)}' style='text-decoration: none;'>{flow_text(text)}</a>" for text, path in message_links(model, message)]
        label += "<br/>" + " · ".join(anchors)
        arrow = "-.->" if message["kind"] == "response" else "-->"
        lines.append(f'  {nodes[message["source"]["id"]]} {arrow}|"{label}"| {nodes[message["target"]["id"]]}')
    for identifier, reference in sorted(references.items()):
        lines.append(f'  click {nodes[identifier]} href "{github_url(context, output_path(reference["kind"], identifier))}" "Open entity" _top')
    return "\n".join(lines)


def sequence(model, messages):
    references = {r["id"]: r for m in messages for r in (m["source"], m["target"])}
    nodes = {identifier: f"N{n}" for n, identifier in enumerate(sorted(references))}
    lines = ["sequenceDiagram"]
    for identifier, reference in sorted(references.items()):
        lines.append(f'  participant {nodes[identifier]} as {flow_text(entity(model, reference)["name"])}')
    for m in messages:
        arrow = "-->>" if m["kind"] == "response" else "->>"
        label = f'{m["number"]}. {flow_text(m["annotation"]["text"])} — {m["interface"]["id"]} v{flow_text(m["interface"]["version"])}'
        if m["envelope"]:
            label += f' — Envelope {m["envelope"]["id"]} v{flow_text(m["envelope"]["version"])}'
        if m["responseTo"]:
            label += f' — response to step {m["responseTo"]}'
        lines.append(f'  {nodes[m["source"]["id"]]}{arrow}{nodes[m["target"]["id"]]}: {label}')
    return "\n".join(lines)


def used_views(model):
    usages = {}
    for view in model["views"].values():
        messages = scenario(model, view) if view["kind"] == "scenario" else [m for v in view["scenarios"] for m in scenario(model, model["views"][v])]
        for message in messages:
            ids = {message["source"]["id"], message["target"]["id"], message["interface"]["id"], message["payload"]["id"]}
            if message["envelope"]:
                ids.add(message["envelope"]["id"])
            for reference in (message["source"], message["target"]):
                if reference["kind"] == "component":
                    ids.add(model["components"][reference["id"]]["systemId"])
            for identifier in ids:
                usages.setdefault(identifier, set()).add(view["id"])
    return usages


def render(model, context, root):
    env = Environment(loader=FileSystemLoader(root / "templates"), undefined=StrictUndefined,
                      autoescape=False, keep_trailing_newline=True)
    env.filters["md"] = md_text
    pages, usages = {}, used_views(model)
    for kind, folder in KINDS.items():
        if kind == "view":
            continue
        for identifier, obj in sorted(model[FOLDERS_KEY(kind)].items()):
            page = output_path(kind, identifier)
            link = lambda text, target: relative_link(text, target, page)
            details = []
            if kind == "system":
                details.append(("Boundary", md_text(obj["boundary"])))
            if kind == "component":
                parent = model["systems"][obj["systemId"]]
                details.append(("Parent system", link(parent["name"], output_path("system", parent["id"]))))
            if kind == "interface":
                owner = obj["owner"]
                details += [("Owner", link(entity(model, owner)["name"], output_path(owner["kind"], owner["id"]))), ("Protocol", md_text(obj["protocol"]))]
            versions = []
            for version, info in sorted(obj.get("versions", {}).items()):
                artifacts = [link(a["label"], a["path"]) for a in info["artifacts"]]
                envelopes = [link(f"{dc} v{v}", output_path("dataContract", dc)) for dc, values in info.get("envelopes", {}).items() for v in values]
                versions.append({"version": version, "artifacts": artifacts, "envelopes": envelopes})
            backlinks = [link(model["views"][v]["name"], output_path("view", v)) for v in sorted(usages.get(identifier, set()))]
            children = [link(c["name"], output_path("component", c["id"])) for c in model["components"].values() if kind == "system" and c["systemId"] == identifier]
            pages[page] = env.get_template("entity.md.j2").render(entity=obj, kind=kind, details=details, versions=versions, backlinks=backlinks, children=children)
    for identifier, view in sorted(model["views"].items()):
        page = output_path("view", identifier)
        messages = scenario(model, view) if view["kind"] == "scenario" else [m for v in view["scenarios"] for m in scenario(model, model["views"][v])]
        rows = []
        for m in messages:
            link = lambda text, target: relative_link(text, target, page)
            endpoints = " → ".join(link(entity(model, r)["name"], output_path(r["kind"], r["id"])) for r in (m["source"], m["target"]))
            contract = m["interface"]
            envelope = "—" if not m["envelope"] else link(f"{m['envelope']['id']} v{m['envelope']['version']}", output_path("dataContract", m["envelope"]["id"]))
            rows.append({"number": m["number"], "endpoints": endpoints,
                         "interface": link(contract["id"], output_path("interface", contract["id"])), "version": contract["version"],
                         "payload": f"{m['payload']['id']} v{m['payload']['version']}", "envelope": envelope,
                         "annotation": m["annotation"]["text"], "responseTo": m["responseTo"] or "—",
                         "references": " · ".join(link(text, path) for text, path in message_links(model, m)),
                         "scenario": link(model["views"][m["viewId"]]["name"], output_path("view", m["viewId"]))})
        pages[page] = env.get_template("view.md.j2").render(view=view, flowchart=flowchart(model, messages, context, view["kind"] == "overview"), sequence=sequence(model, messages) if view["kind"] == "scenario" else None, rows=rows)
    groups = []
    for kind, folder in KINDS.items():
        groups.append({"name": folder, "links": [relative_link(f"{o['id']} — {o['name']}", output_path(kind, o["id"]), "docs/generated/index.md") for _, o in sorted(model[FOLDERS_KEY(kind)].items())]})
    pages["docs/generated/index.md"] = env.get_template("index.md.j2").render(groups=groups)
    pages["docs/generated/.context.json"] = json.dumps(context, indent=2) + "\n"
    return pages


def render_context(root, args):
    saved = root / "docs/generated/.context.json"
    context = read_json(saved) if args.command == "check" and saved.exists() else {}
    if not context.get("repository"):
        context["repository"] = os.environ.get("GITHUB_REPOSITORY", "")
        if not context["repository"]:
            origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True).stdout.strip()
            match = re.fullmatch(r"(?:https://github.com/|git@github.com:)([^/]+/[^/]+?)(?:\.git)?", origin)
            if match:
                context["repository"] = match.group(1)
    if not context.get("ref"):
        context["ref"] = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True).stdout.strip() or "main"
    if args.repository:
        context["repository"] = args.repository
    if args.ref:
        context["ref"] = args.ref
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", context["repository"]):
        raise ValueError("Cannot infer the GitHub repository. Pass --repository OWNER/REPO.")
    return context


def write_pages(root, pages, check=False):
    generated = root / "docs/generated"
    if not generated.resolve().is_relative_to(root.resolve()):
        raise ValueError("Generated output must stay inside the repository")
    actual = {p.relative_to(root).as_posix() for p in generated.rglob("*") if p.is_file()}
    stale = [path for path, content in pages.items() if not (root / path).is_file() or (root / path).read_text(encoding="utf-8") != content]
    orphaned = actual - pages.keys()
    if check and (stale or orphaned):
        raise ValueError("Generated documentation is stale; run generate.\n" + "\n".join(sorted(set(stale) | orphaned)))
    if not check:
        for path in orphaned:
            (root / path).unlink()
        for path, content in pages.items():
            destination = root / path
            if not destination.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Output escapes repository: {path}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")


def check_links(root):
    for directory, children, names in os.walk(root):
        children[:] = [n for n in children if n not in IGNORED and not (Path(directory) / n).is_symlink()]
        for name in names:
            if not name.endswith(".md"):
                continue
            page = Path(directory) / name
            source = re.sub(r"```.*?```", "", page.read_text(encoding="utf-8"), flags=re.S)
            for destination in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", source):
                url = urlsplit(destination)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = (page.parent / unquote(url.path)).resolve()
                if not target.is_relative_to(root.resolve()) or not target.exists():
                    raise ValueError(f"Broken local link in {page.relative_to(root)}: {destination}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "generate", "check"])
    parser.add_argument("--repository", help="GitHub OWNER/REPO; inferred from origin or CI")
    parser.add_argument("--ref", help="Link revision; inferred on generate, recorded for reproducible checks")
    args = parser.parse_args(argv)
    try:
        model = validate(ROOT)
        if args.command != "validate":
            pages = render(model, render_context(ROOT, args), ROOT)
            write_pages(ROOT, pages, check=args.command == "check")
            check_links(ROOT)
        print("OK: " + ", ".join(f"{len(model[k])} {folder}" for k, folder in FOLDERS.items()))
        return 0
    except (ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
