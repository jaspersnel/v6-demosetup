from pathlib import Path
from uuid import uuid4
import argparse

import yaml


parser = argparse.ArgumentParser(description='Set up a demo Vantage6 infrastructure.')
parser.add_argument('--server-ip', '-s', type=str, help='what IP will the server live (in case of non-local?', default='host.docker.internal')

args = parser.parse_args()

orgs = [{'database': db} for db in Path('databases').glob('*.csv') if db.is_file()]

entity_yaml = {
    'organizations': [],
    'collaborations': [],
    'nodes': []
}
collaboration = {
    'name': 'Vantage6-demo',
    'encrypted': False,
    'participants': []
}

# Add one org for every name and add them to a collaboration
for org in orgs:
    name = org['database'].stem
    api_key = str(uuid4())

    org['name'] = name
    org['api_key'] = api_key

    collaboration['participants'].append({
        'name': name,
        'api-key': api_key,
    })

    organization = {
        'name': name,
        'domain': f'{name}.nl',
        'address1': f'{name}street 42',
        'address2': '',
        'zipcode': '1234AB',
        'country': 'Netherlands',
        'public_key': '',
        'users': [
            {
                'username': f'{name}-user',
                'password': f'{name}-password',
                'firstname': 'Firstname',
                'lastname': 'Lastname',
                'email': f'user@{name}.nl'
            }
        ]
    }

    entity_yaml['organizations'].append(organization)

entity_yaml['collaborations'].append(collaboration)

out_dir = Path('v6-data')
out_dir.mkdir(exist_ok=True)

# Write out files
script = ''

server_dir = out_dir / 'server'
server_dir.mkdir(exist_ok=True)
with open(server_dir / 'entities.yaml', 'w+') as f:
    yaml.safe_dump(entity_yaml, f)

with open(Path('skeletons/server-config-skeleton.yaml')) as f:
    server_config = yaml.safe_load(f)

# In the future maybe do something with config

with open(server_dir / 'config.yaml', 'w') as f:
    yaml.safe_dump(server_config, f)

# Add server calls to run.sh
script = script + f'vserver start --user -c {(server_dir / "config.yaml").resolve()}\n'
script = script + f'vserver import --user --drop-all -c {(server_dir / "config.yaml").resolve()} {(server_dir / "entities.yaml").resolve()}\n'

# Write the node configs
with open(Path('skeletons/node-config-skeleton.yaml')) as f:
    node_skeleton = yaml.safe_load(f)

for org in orgs:
    node = node_skeleton.copy()

    node['application']['databases']['default'] = str(org['database'].resolve())
    node['application']['api_key'] = org['api_key']

    node['application']['server_url'] = f'http://{args.server_ip}'
    node['application']['encryption']['enabled'] = False
    node['application']['encryption']['private_key'] = ''

    output_file = out_dir / f'{org["name"]}.yaml'
    with open(output_file, 'w+') as f:
        yaml.safe_dump(node, f)

    # Add run command for node to run.sh
    script = script + f'vnode start -c {output_file.resolve()}\n'

with open('run.sh', 'w') as f:
    f.write(script)