"""Behavior checks for views, shared references, and generated navigation."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate as g


REPOSITORY = Path(__file__).resolve().parents[1]


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copytree(REPOSITORY / 'contracts', self.root / 'contracts')
        (self.root / 'docs/notes').mkdir(parents=True)
        (self.root / 'docs/notes/invoice-mapping.md').write_text('# Mapping\n')
        self.catalog = json.loads((REPOSITORY / 'catalog/catalog.json').read_text())
        self.scenario = self.catalog['views'][0]
        self.root_patch = patch.object(g, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def assert_invalid(self, text):
        with self.assertRaisesRegex(ValueError, text):
            g.validate(self.catalog)

    def test_invoice_steps_reuse_interface_and_reverse_response(self):
        g.validate(self.catalog)
        entries = g.connections(self.catalog, self.scenario)
        self.assertEqual([e['number'] for e in entries], [1, 2, 3])
        self.assertEqual([e['interface']['id'] for e in entries], ['IF-001', 'IF-003', 'IF-003'])
        self.assertEqual((entries[2]['source'], entries[2]['target']), ('erp', 'billing-worker'))
        graph = g.flowchart(self.catalog, entries)
        self.assertEqual(graph.count('/docs/interfaces/IF-003.md'), 2)
        self.assertIn('S_erp -.->|"3. Return invoice ID"| STEP_003 -.-> S_billing_worker', graph)
        self.assertNotIn('IF-004', graph)
        self.assertNotIn('S_crm', graph)
        messages = g.sequence(self.catalog, entries)
        self.assertIn('  autonumber\n', messages)
        self.assertIn('S_erp-->>S_billing_worker: IF-003 — Return invoice ID', messages)

    def test_annotation_and_interface_links_have_independent_destinations(self):
        page = g.render_view(self.catalog, self.scenario)
        self.assertIn("<a href='https://github.com/benedikt-roth/integration-atlas-demo/blob/main/docs/notes/invoice-mapping.md'>2. Create invoice using the mapping rules</a>", page)
        self.assertIn('[Create invoice using the mapping rules](../notes/invoice-mapping.md)', page)
        self.assertIn('[IF-003](../interfaces/IF-003.md)', page)
        messages = g.sequence(self.catalog, g.connections(self.catalog, self.scenario))
        self.assertNotIn('<a ', messages)
        self.assertNotIn('href', messages)

    def test_overview_is_filtered_without_sequence_numbers(self):
        page = g.render_view(self.catalog, self.catalog['views'][1])
        self.assertIn('IF-004', page)
        self.assertNotIn('IF-002', page)
        self.assertNotIn('sequenceDiagram', page)
        self.assertNotIn('STEP_', page)

    def test_backlinks_deduplicate_repeated_interface(self):
        links = g.backlinks(self.catalog, 'docs/interfaces/IF-003.md', interface_id='IF-003')
        self.assertEqual(links.count('[Invoice creation]'), 1)
        self.assertEqual(links.count('[Invoicing subdomain]'), 1)
        links = g.backlinks(self.catalog, 'docs/systems/erp.md', system_id='erp')
        self.assertEqual(links.count('[Invoice creation]'), 1)
        self.assertEqual(g.backlinks(self.catalog, 'docs/systems/crm.md', system_id='crm'), '')

    def test_shared_metadata_changes_propagate_without_editing_views(self):
        original_views = copy.deepcopy(self.catalog['views'])
        interface = next(i for i in self.catalog['interfaces'] if i['id'] == 'IF-003')
        interface['name'] = 'Revised invoice API'
        interface['deployed_version'] = '2.2.0'
        interface['artifact'] = 'contracts/erp/invoices-2.2.0.openapi.json'
        spec = json.loads((self.root / 'contracts/erp/invoices-2.1.0.openapi.json').read_text())
        spec['info']['version'] = '2.2.0'
        (self.root / interface['artifact']).write_text(json.dumps(spec))
        g.validate(self.catalog)
        outputs = g.render(self.catalog)
        for page in ('README.md', 'docs/interfaces/IF-003.md', 'docs/views/invoice-creation.md',
                     'docs/views/invoicing-overview.md'):
            self.assertIn('2.2.0', outputs[page])
            self.assertIn('Revised invoice API', outputs[page])
        self.assertEqual(self.catalog['views'], original_views)

    def test_catalog_without_views_still_renders(self):
        self.catalog.pop('views')
        g.validate(self.catalog)
        outputs = g.render(self.catalog)
        self.assertFalse(any(path.startswith('docs/views/') for path in outputs))
        self.assertNotIn('Used in views', outputs['docs/interfaces/IF-003.md'])

    def test_generated_page_can_be_annotation_target_before_first_generation(self):
        annotation = self.scenario['steps'][1]['annotation']
        annotation['target'] = 'docs/views/invoicing-overview.md'
        self.assertFalse((self.root / annotation['target']).exists())
        g.validate(self.catalog)

    def test_target_with_spaces_uses_encoded_links_in_both_presentations(self):
        (self.root / 'docs/notes/mapping rules.md').write_text('# Mapping\n')
        self.scenario['steps'][1]['annotation']['target'] = 'docs/notes/mapping rules.md'
        g.validate(self.catalog)
        page = g.render_view(self.catalog, self.scenario)
        self.assertIn('/docs/notes/mapping%20rules.md', page)
        self.assertIn('(../notes/mapping%20rules.md)', page)

    def test_annotation_text_is_escaped_for_mermaid_and_markdown(self):
        annotation = self.scenario['steps'][1]['annotation']
        annotation['text'] = 'Map "quoted" <input> | use [rules]; #1'
        graph = g.flowchart(self.catalog, g.connections(self.catalog, self.scenario))
        self.assertIn('#34;quoted#34;', graph)
        self.assertIn('#60;input#62;', graph)
        self.assertIn('#124;', graph)
        messages = g.sequence(self.catalog, g.connections(self.catalog, self.scenario))
        self.assertIn('#59;', messages)
        self.assertNotIn('<input>', messages)
        page = g.render_view(self.catalog, self.scenario)
        self.assertIn('\\[rules\\]', page)

    def test_invalid_views_are_rejected(self):
        original = copy.deepcopy(self.catalog)
        cases = [
            ('unknown interface', lambda c: c['views'][0]['steps'][0].update(interface_id='IF-999')),
            ('Duplicate view ID', lambda c: c['views'].append(copy.deepcopy(c['views'][0]))),
            ('filename-safe', lambda c: c['views'][0].update(id='../escape')),
            ('unsupported view kind', lambda c: c['views'][0].update(kind='other')),
            ('at least one step', lambda c: c['views'][0].update(steps=[])),
            ('direction must', lambda c: c['views'][0]['steps'][0].update(direction='sideways')),
            ('annotation text', lambda c: c['views'][0]['steps'][0].update(annotation={'text': ''})),
            ('derived from steps', lambda c: c['views'][0].update(interface_ids=['IF-003'])),
            ('duplicate overview interface', lambda c: c['views'][1].update(interface_ids=['IF-003', 'IF-003'])),
        ]
        for expected, change in cases:
            with self.subTest(expected=expected):
                self.catalog = copy.deepcopy(original)
                change(self.catalog)
                self.assert_invalid(expected)

    def test_invalid_annotation_targets_are_rejected(self):
        annotation = self.scenario['steps'][1]['annotation']
        targets = ['../outside.md', '/etc/example.md', 'https://example.com/page.md',
                   'docs/notes/invoice-mapping.md#heading', 'docs/notes/invoice-mapping.md?x=1',
                   'docs/../README.md', 'docs/notes/missing.md', 'catalog/catalog.json']
        for target in targets:
            with self.subTest(target=target):
                annotation['target'] = target
                self.assert_invalid('target')

    def test_check_detects_stale_and_orphaned_view_pages(self):
        outputs = g.render(self.catalog)
        g.write_outputs(outputs)
        g.write_outputs(outputs, check=True)
        file = self.root / 'docs/views/invoice-creation.md'
        file.write_text('stale')
        with self.assertRaisesRegex(ValueError, 'Stale generated file'):
            g.write_outputs(outputs, check=True)
        g.write_outputs(outputs)
        (self.root / 'docs/views/removed-view.md').write_text('orphan')
        with self.assertRaisesRegex(ValueError, 'Orphaned generated page'):
            g.write_outputs(outputs, check=True)

    def test_broken_relative_link_fails_link_check(self):
        (self.root / 'broken.md').write_text('[Missing](docs/absent.md)')
        with self.assertRaisesRegex(ValueError, 'broken link'):
            g.check_links()

    def test_link_check_ignores_dependency_and_build_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('[Guide](guide.md)')
            (root / 'guide.md').write_text('# Guide')
            for folder in ('likec4-poc/node_modules/library', 'likec4-poc/dist'):
                target = root / folder
                target.mkdir(parents=True)
                (target / 'README.md').write_text('[Broken third-party link](absent.md)')
            with patch.object(g, 'ROOT', root):
                self.assertEqual(g.check_links(), 1)


if __name__ == '__main__':
    unittest.main()
