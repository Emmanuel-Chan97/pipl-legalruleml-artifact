"""Run both official schema checks and the Article 57 source trace offline."""
import hashlib
from pathlib import Path
import subprocess
import sys

from lxml import etree

from verify_anchors import verify

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT / 'schema-akn30'
HASHES = {
    'akomantoso30.xsd': '6f61fe84cbb6f8cb0e8418cd67b74a63da9990e6573b5a3491f623184f45c4fd',
    'xml.xsd': '61960fb3131e38022caad5360e2f33a3382578ab3c80cd58bd74320ede61b20c',
}


def main():
    for filename, expected in HASHES.items():
        actual = hashlib.sha256((SCHEMAS / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Schema checksum mismatch for {filename}')
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    akn_schema = etree.XMLSchema(etree.parse(str(SCHEMAS / 'akomantoso30.xsd'), parser))
    akn_schema.assertValid(etree.parse(str(ROOT / 'art57.akn.xml'), parser))
    print('OASIS Akoma Ntoso 3.0 XSD and pinned checksums: PASS', flush=True)
    subprocess.run(
        [sys.executable, str(ROOT.parent / 'replication' / 'profile.py'), str(ROOT / 'art57.lrml')],
        check=True,
    )
    verify()


if __name__ == '__main__':
    main()
