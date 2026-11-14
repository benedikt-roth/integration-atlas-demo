#!/usr/bin/env python3
"""Check the actual LikeC4 export against the source catalog, not just DSL text."""

import json
from pathlib import Path
import sys

from generate import REPOSITORY, atlas, identifier, url


def verify(catalog, model):
    interfaces = {i['id']: i for i in catalog['interfaces']}
    relations = {r['metadata']['interfaceId']: r for r in model['relations'].values()}
    assert set(relations) == set(interfaces), 'Native model interface set differs from catalog'
    assert set(model['elements']) == {identifier(s['id']) for s in catalog['systems']}
    for key, interface in interfaces.items():
        relation = relations[key]
        assert relation['metadata']['deployedVersion'] == interface['deployed_version'], key
        assert relation['source']['model'] == identifier(interface['source']), key
        assert relation['target']['model'] == identifier(interface['target']), key
        links = {link['url'] for link in relation['links']}
        assert url(catalog, f'docs/interfaces/{key}.md') in links, key
        assert url(catalog, interface['artifact']) in links, key

    limitations = []
    for view in catalog.get('views', []):
        native = model['views'][identifier(view['id'])]
        if view['kind'] == 'overview':
            actual = {model['relations'][r]['metadata']['interfaceId']
                      for edge in native['edges'] for r in edge['relations']}
            assert actual == set(view['interface_ids']), f'{view["id"]}: incorrect filtered interfaces'
            continue
        assert len(native['flow']) == len(view['steps']), f'{view["id"]}: step count changed'
        by_id = {edge['id']: edge for edge in native['edges']}
        for number, (key, step) in enumerate(zip(native['flow'], view['steps']), 1):
            edge = by_id[key]
            interface = interfaces[step['interface_id']]
            reverse = step.get('direction', 'forward') == 'reverse'
            source, target = interface['source'], interface['target']
            if reverse:
                source, target = target, source
            assert (edge['source'], edge['target']) == (identifier(source), identifier(target))
            assert edge['label'] == interface['id'] + ' — ' + step['annotation']['text']
            assert edge['description']['txt'] == interface['summary']
            assert edge['line'] == ('dashed' if reverse else 'solid')
            assert 'md' in edge['notes'], 'Notes must render Markdown links rather than literal markup'
            notes = edge['notes']['md']
            assert url(catalog, f'docs/interfaces/{interface["id"]}.md') in notes
            assert url(catalog, interface['artifact']) in notes
            assert interface['deployed_version'] in notes
            if step['annotation'].get('target'):
                assert url(catalog, step['annotation']['target']) in notes
            actual = {model['relations'][r]['metadata']['interfaceId'] for r in edge['relations']}
            if actual != {interface['id']}:
                assert reverse, f'{view["id"]} step {number}: forward relationship association changed'
                limitations.append(f'{view["id"]} step {number}: native relation lookup selects '
                                   f'{sorted(actual)} rather than {interface["id"]}. '
                                   'Use the explicit canonical links in step notes.')
    return limitations


if __name__ == '__main__':
    catalog = json.loads((REPOSITORY / 'catalog/catalog.json').read_text())
    model = json.loads(Path(sys.argv[1]).read_text())
    limitations = verify(catalog, model)
    print('PASS: native systems, interface metadata, filtered views, ordered data flows, and explicit documentation links match the catalog.')
    for limitation in limitations:
        print('KNOWN LIKEC4 LIMITATION: ' + limitation)
