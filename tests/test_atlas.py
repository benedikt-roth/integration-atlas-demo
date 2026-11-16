"""Behavioral checks against the real CUE validator and renderer."""
import copy
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("atlas", ROOT / "scripts/atlas.py")
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)
CONTEXT = {"repository": "example/fork", "ref": "feature/docs"}


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for directory in ("model", "schemas", "contracts", "templates", "docs"):
            shutil.copytree(ROOT / directory, self.root / directory)
        shutil.copy(ROOT / "README.md", self.root / "README.md")
        self.view = "model/views/VIEW-001--example-request.json"
        self.interface = "model/interfaces/IF-001--example-api.json"

    def edit(self, path, change):
        file = self.root / path
        obj = json.loads(file.read_text())
        change(obj)
        file.write_text(json.dumps(obj))

    def rejected(self):
        with self.assertRaisesRegex(ValueError, "CUE validation failed"):
            atlas.validate(self.root)

    def routed(self):
        """Introduce a real distinct router and target only in test fixtures."""
        system = {"id": "SYS-002", "name": "External target", "description": "Target", "boundary": "external"}
        router = {"id": "CMP-002", "name": "Router", "description": "Pass through", "systemId": "SYS-001"}
        target = {"id": "IF-002", "name": "Target API", "description": "Target contract",
                  "owner": {"kind": "system", "id": "SYS-002"}, "protocol": "HTTPS",
                  "versions": {"4.2.0": {"artifacts": [{"label": "Target OpenAPI", "kind": "openapi", "path": "contracts/target-4.2.0.json"}]}}}
        for path, value in [("model/systems/SYS-002--target.json", system),
                            ("model/components/CMP-002--router.json", router),
                            ("model/interfaces/IF-002--target.json", target),
                            ("contracts/target-4.2.0.json", {"openapi": "3.1.0", "info": {"version": "4.2.0"}})]:
            (self.root / path).write_text(json.dumps(value))
        self.edit(self.interface, lambda o: o.update(owner={"kind": "component", "id": "CMP-002"}))
        def route(view):
            view["steps"][0]["interface"] = {"id": "IF-002", "version": "4.2.0"}
            view["steps"][0]["transport"] = {
                "viaInterface": {"id": "IF-001", "version": "1.0.0"},
                "envelope": {"id": "DC-001", "version": "2.0.0"}, "envelopeScope": "router-leg"}
        self.edit(self.view, route)

    def test_seed_has_exactly_one_of_each_entity_and_validates(self):
        model = atlas.validate(self.root)
        self.assertEqual({k: len(v) for k, v in model.items()}, {k: 1 for k in atlas.FOLDERS})
        messages = atlas.scenario(model, model["views"]["VIEW-001"])
        self.assertEqual([m["interface"]["id"] for m in messages], ["IF-001", "IF-001"])
        self.assertEqual(messages[1]["source"], messages[0]["target"])
        self.assertEqual(messages[1]["responseTo"], 1)

    def test_dangling_parent_and_typed_owner_are_rejected(self):
        self.edit("model/components/CMP-001--example-worker.json", lambda o: o.update(systemId="SYS-MISSING"))
        self.rejected()
        self.edit("model/components/CMP-001--example-worker.json", lambda o: o.update(systemId="SYS-001"))
        self.edit(self.interface, lambda o: o.update(owner={"kind": "system", "id": "CMP-001"}))
        self.rejected()

    def test_unknown_interface_version_and_annotation_target_are_rejected(self):
        for field, value in [("id", "IF-MISSING"), ("version", "9.9.9")]:
            with self.subTest(field=field):
                self.edit(self.view, lambda o: o["steps"][0]["interface"].update({field: value}))
                self.rejected()
                self.edit(self.view, lambda o: o["steps"][0].update(interface={"id": "IF-001", "version": "1.0.0"}))
        self.edit(self.view, lambda o: o["steps"][0]["annotation"]["links"][0]["target"].update(id="IF-MISSING"))
        self.rejected()

    def test_closed_schema_and_filename_id_are_enforced(self):
        self.edit(self.interface, lambda o: o.update(consummers=[]))
        self.rejected()
        self.edit(self.interface, lambda o: o.pop("consummers"))
        self.edit(self.interface, lambda o: o.update(id="IF-DIFFERENT"))
        self.rejected()

    def test_duplicate_files_and_json_keys_do_not_overwrite(self):
        original = self.root / self.interface
        original.with_name("IF-001--duplicate.json").write_text(original.read_text())
        with self.assertRaisesRegex(ValueError, "Duplicate entity file ID"):
            atlas.validate(self.root)
        original.with_name("IF-001--duplicate.json").unlink()
        original.write_text('{"id":"IF-001","id":"IF-OTHER"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            atlas.validate(self.root)

    def test_artifact_version_and_presence_are_checked(self):
        self.edit("contracts/example-api-1.0.0.openapi.json", lambda o: o["info"].update(version="9.0.0"))
        self.rejected()
        self.edit("contracts/example-api-1.0.0.openapi.json", lambda o: o["info"].update(version="1.0.0"))
        (self.root / "contracts/example-api-1.0.0.openapi.json").unlink()
        self.rejected()

    def test_xsd_version_and_unsafe_targets_are_rejected(self):
        xsd = self.root / "contracts/example-envelope-2.0.0.xsd"
        original = xsd.read_text()
        xsd.write_text(original.replace('version="2.0.0"', 'version="3.0.0"'))
        self.rejected()
        xsd.write_text(original)
        self.edit(self.view, lambda o: o["steps"][0]["annotation"]["links"].append({"label": "Unsafe", "target": {"kind": "file", "path": "../README.md"}}))
        self.rejected()

    def test_forward_response_and_duplicate_step_ids_are_rejected(self):
        self.edit(self.view, lambda o: o["steps"].reverse())
        self.rejected()
        self.edit(self.view, lambda o: o["steps"].reverse())
        self.edit(self.view, lambda o: o["steps"].append(copy.deepcopy(o["steps"][0])))
        self.rejected()

    def test_routing_preserves_target_contract_on_return_hops(self):
        self.routed()
        model = atlas.validate(self.root)
        messages = atlas.scenario(model, model["views"]["VIEW-001"])
        self.assertEqual([m["number"] for m in messages], ["1a", "1b", "2a", "2b"])
        self.assertEqual([m["interface"]["id"] for m in messages], ["IF-001", "IF-002", "IF-002", "IF-001"])
        self.assertTrue(all(m["payload"] == {"id": "IF-002", "version": "4.2.0"} for m in messages))
        self.assertEqual([bool(m["envelope"]) for m in messages], [True, False, False, True])
        self.assertEqual(messages[2]["source"]["id"], "SYS-002")
        self.assertEqual(messages[2]["target"]["id"], "CMP-002")
        self.assertEqual(atlas.used_views(model)["DC-001"], {"VIEW-001"})

    def test_end_to_end_envelope_and_unsupported_known_version(self):
        self.routed()
        self.edit(self.view, lambda o: o["steps"][0]["transport"].update(envelopeScope="end-to-end"))
        model = atlas.validate(self.root)
        self.assertTrue(all(m["envelope"] for m in atlas.scenario(model, model["views"]["VIEW-001"])))
        new_xsd = self.root / "contracts/envelope-3.0.0.xsd"
        new_xsd.write_text((self.root / "contracts/example-envelope-2.0.0.xsd").read_text().replace('version="2.0.0"', 'version="3.0.0"'))
        self.edit("model/data-contracts/DC-001--example-envelope.json", lambda o: o["versions"].update({"3.0.0": {"artifacts": [{"label": "XSD", "kind": "xsd", "path": "contracts/envelope-3.0.0.xsd"}]}}))
        self.edit(self.view, lambda o: o["steps"][0]["transport"]["envelope"].update(version="3.0.0"))
        self.rejected()

    def test_overview_projects_scenario_without_new_usage(self):
        overview = {"id": "VIEW-OVERVIEW", "name": "Domain", "description": "Projection", "kind": "overview", "scenarios": ["VIEW-001"]}
        file = self.root / "model/views/VIEW-OVERVIEW--domain.json"
        file.write_text(json.dumps(overview))
        model = atlas.validate(self.root)
        pages = atlas.render(model, CONTEXT, self.root)
        page = pages["docs/generated/views/VIEW-OVERVIEW.md"]
        self.assertIn("IF-001", page)
        self.assertNotIn("sequenceDiagram", page)
        self.assertEqual(atlas.used_views(model)["IF-001"], {"VIEW-001", "VIEW-OVERVIEW"})
        overview["scenarios"] = ["VIEW-OVERVIEW"]
        file.write_text(json.dumps(overview))
        self.rejected()

    def test_links_are_independent_and_sequence_contains_no_anchors(self):
        self.edit(self.view, lambda o: o["steps"][0]["annotation"].update(text='Quotes " pipes | <angle>; #hash & text'))
        model = atlas.validate(self.root)
        pages = atlas.render(model, CONTEXT, self.root)
        page = pages["docs/generated/views/VIEW-001.md"]
        self.assertIn("#34;", page)
        self.assertIn("#124;", page)
        self.assertIn("style='text-decoration: none;'", page)
        self.assertIn("https://github.com/example/fork/blob/feature/docs/docs/notes/example.md", page)
        self.assertIn("[Notes](../../notes/example.md)", page)
        sequence = page.split("sequenceDiagram", 1)[1].split("```", 1)[0]
        self.assertNotIn("<a ", sequence)
        self.assertEqual(pages["docs/generated/interfaces/IF-001.md"].count("[Example request]"), 1)
        self.assertIn("No actual usage", pages["docs/generated/data-contracts/DC-001.md"])

    def test_drift_orphans_local_links_and_fork_context(self):
        model = atlas.validate(self.root)
        pages = atlas.render(model, CONTEXT, self.root)
        atlas.write_pages(self.root, pages)
        atlas.write_pages(self.root, pages, check=True)
        atlas.check_links(self.root)
        orphan = self.root / "docs/generated/obsolete.md"
        orphan.write_text("obsolete")
        with self.assertRaisesRegex(ValueError, "stale"):
            atlas.write_pages(self.root, pages, check=True)
        atlas.write_pages(self.root, pages)
        self.assertFalse(orphan.exists())
        page = self.root / "docs/generated/views/VIEW-001.md"
        page.write_text(page.read_text() + "\n[Broken](missing.md)\n")
        with self.assertRaisesRegex(ValueError, "stale"):
            atlas.write_pages(self.root, pages, check=True)
        with self.assertRaisesRegex(ValueError, "Broken local link"):
            atlas.check_links(self.root)
        pages_other = atlas.render(model, {"repository": "another/project", "ref": "main"}, self.root)
        self.assertIn("https://github.com/another/project/blob/main/", pages_other["docs/generated/views/VIEW-001.md"])

    def test_events_reverse_direction_relative_to_interface_owner(self):
        self.edit(self.view, lambda o: o.update(steps=[dict(o["steps"][0], kind="event")]))
        model = atlas.validate(self.root)
        message = atlas.scenario(model, model["views"]["VIEW-001"])[0]
        self.assertEqual(message["source"]["id"], "SYS-001")
        self.assertEqual(message["target"]["id"], "CMP-001")

    def test_generate_infers_fork_and_check_uses_recorded_context(self):
        atlas.subprocess.run(["git", "init", "--initial-branch=fork-branch"], cwd=self.root, capture_output=True, check=True)
        atlas.subprocess.run(["git", "remote", "add", "origin", "git@github.com:another/my-atlas.git"], cwd=self.root, capture_output=True, check=True)
        args = argparse.Namespace(command="generate", repository=None, ref=None)
        with patch.dict(atlas.os.environ, {"GITHUB_REPOSITORY": "", "GITHUB_HEAD_REF": "", "GITHUB_REF_NAME": ""}):
            inferred = atlas.render_context(self.root, args)
        self.assertEqual(inferred, {"repository": "another/my-atlas", "ref": "fork-branch"})
        model = atlas.validate(self.root)
        atlas.write_pages(self.root, atlas.render(model, inferred, self.root))
        args.command = "check"
        with patch.dict(atlas.os.environ, {"GITHUB_REPOSITORY": "somewhere/else", "GITHUB_REF_NAME": "detached"}):
            self.assertEqual(atlas.render_context(self.root, args), inferred)


if __name__ == "__main__":
    unittest.main()
