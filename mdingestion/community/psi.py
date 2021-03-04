from .base import Community
from ..service_types import SchemaType, ServiceType


class PsiDatacite(Community):
    NAME = 'psi'
    IDENTIFIER = NAME
    URL = 'https://oai.datacite.org/oai'
    SCHEMA = SchemaType.DataCite
    SERVICE_TYPE = ServiceType.OAI
    OAI_METADATA_PREFIX = 'oai_datacite'
    OAI_SET = 'ETHZ.PSI'

    def update(self, doc):
        doc.discipline = self.discipline(doc, 'Basic Biological and Medical Research')
