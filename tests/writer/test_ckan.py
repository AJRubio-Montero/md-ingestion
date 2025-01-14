import os

import pytest

from mdingestion.community.darus import DarusDatacite
from mdingestion.community.herbadrop import Herbadrop
from mdingestion.writer import CKANWriter

from tests.common import TESTDATA_DIR


def test_darus_oai_datacite():
    xmlfile = os.path.join(TESTDATA_DIR, 'darus', 'raw', '02baec53-8e79-5611-981e-11df59b824e4.xml')
    reader = DarusDatacite()
    doc = reader.read(xmlfile)
    writer = CKANWriter()
    result = writer.json(doc)
    assert "darus" == result['owner_org']
    assert 'Deep enzymology data' in result['title']
    assert '02baec53-8e79-5611-981e-11df59b824e4' == result['name']
    assert 'active' == result['state']
    assert 'Medicine' in [tag['name'] for tag in result['tags']]
    fields = {}
    for field in result['extras']:
        fields[field['key']] = field['value']
    assert 'Deep enzymology data' in fields['fulltext']
    assert "Life Sciences; Medicine" == fields["Discipline"]
    assert '2020' == fields['PublicationYear']
    assert '2020-01-30T00:00:00Z' == fields['TemporalCoverage:BeginDate']
    # assert 63715939200 == fields['TempCoverageBegin']  # TODO: fails on ci
    assert 'true' == fields['OpenAccess']
    # assert '4c034878509472f5514acb44dca9ece16e49b75af515e348610452d941e7a0cd' == result['version']


def test_herbdrop_json():
    jsonfile = os.path.join(TESTDATA_DIR, 'herbadrop', 'raw', '0d9e8478-3d92-5a5f-92cb-eb678e8e48dd.json')
    reader = Herbadrop()
    doc = reader.read(jsonfile)
    writer = CKANWriter()
    result = writer.json(doc)
    fields = {}
    for field in result['extras']:
        fields[field['key']] = field['value']
    assert 'Gentiana ×marcailhouana Rouy' in fields['fulltext']
    assert 'StillImage|PRESERVED_SPECIMEN' in fields['fulltext']
