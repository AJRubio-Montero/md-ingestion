import shapely

from .base import XMLReader
from ..sniffer import OAISniffer
from ..util import convert_to_lon_180


class DublinCoreReader(XMLReader):
    SNIFFER = OAISniffer

    def parse(self, doc):
        doc.title = self.find('title')
        doc.description = self.find('description')
        doc.keywords = self.find('subject')
        doc.discipline = self.discipline(doc)
        doc.doi = self.find_doi('metadata.identifier')
        doc.pid = self.find_pid('metadata.identifier')
        doc.source = self.find_source('metadata.identifier')
        doc.related_identifier = self.related_identifier()
        doc.creator = self.find('creator')
        doc.publisher = self.find('publisher')
        doc.contributor = self.find('contributor')
        doc.publication_year = self.find('date')
        doc.rights = self.find('rights')
        doc.funding_reference = self.funding_reference()
        doc.contact = doc.publisher
        doc.language = self.find('language')
        doc.resource_type = self.find('type')
        doc.format = self.find('format')
        temporal = self.temporal_coverage()
        if 'start' in temporal.keys(): 
            doc.temporal_coverage_end = string_aux['start']       
        if 'end' in temporal.keys(): 
            doc.temporal_coverage_end = string_aux['end']
        doc.geometry = self.find_geometry()
        doc.places = self.places()
        doc.size = self.find('extent')
        doc.version = self.find('hasVersion')

    def related_identifier(self):
        urls = self.find('relation')
        urls.extend(self.find('source'))
        return urls

    def funding_reference(self):
        funding_refs = [info for info in self.find('relation') if 'info:eu-repo/grantAgreement' in info]
        return funding_refs

    def places(self):
        # ajrm comment: It is very optimistic find always a place in <dc:coverage> ... </dc:coverage>
        places = [s.text.strip() for s in self.parser.doc.find_all('spatial') if not s.attrs]
        return places

    def _dc_item_to_dict(self, string_aux):
        string_list = string_aux.replace('; ',',').replace(';',',').replace('=',',').split(',')
        string_dict = {string_list[i]: string_list[i + 1] for i in range(0, len(string_list)-1, 2)}
        return string_dict
    
    def temporal_coverage(self):
        string_aux = None
        string_dict = {}
        if self.parser.doc.find('coverage', attrs={'xsi:type': 'dcterms:Period'}) or 
            self.parser.doc.find('temporal', attrs={'xsi:type': 'dcterms:Period'}):
                string_aux = self.parser.doc.find('temporal', attrs={'xsi:type': 'dcterms:Period'})
                
        if string_aux:
            # https://www.dublincore.org/specifications/dublin-core/dcmi-period/
            # <dc:coverage xsi:type="dcterms:Period">name=Perth International Arts Festival, 2000; start=2000-01-26; end=2000-02-20; scheme=W3C-DTF;</dc:coverage>
            # <dcterms:temporal xsi:type="dcterms:Period">name=Perth International Arts Festival, 2000; start=2000-01-26; end=2000-02-20; scheme=W3C-DTF;</dcterms:temporal>
            if string_aux.find('start'): 
                string_dict = self._dc_item_to_dict(string_aux)
            elif not string_aux.find('='):
                # ajrm: if DC non-normative, dangerous without keys
                # <dcterms:temporal xsi:type="dcterms:Period">2000-01-26,2000-02-20</dcterms:temporal>
                # <dcterms:temporal xsi:type="dcterms:Period">2000-01-26 2000-02-20</dcterms:temporal>
                string_list= string_aux.string_aux.replace(',',' ').split()
                string_dict['start'] = string_list[0]
                if len(string_list) > 1 : 
                    string_dict['end'] = string_list[1]
                    
         return string_dict 
    
    
    def _geometry_point(self, point):
        lon = float(point[0])
        lon = convert_to_lon_180(lon)
        lat = float(point[1])
        # point: x=lon, y=lat
        return shapely.geometry.Point(lon, lat)
    
    def _geometry_bbox(self, bbox):
        south = float(bbox[0])
        east = float(bbox[1])
        east = convert_to_lon_180(east)
        north = float(bbox[2])
        west = float(bbox[3])
        west = convert_to_lon_180(west)
        # bbox: minx=west, miny=south, maxx=east, maxy=north
        return shapely.geometry.box(west, south, east, north)
    
    def geometry(self):
        # ajrm: possible issue. As BeatifulSoup could be called as XML, 
        #       then tags and atributes are (Upper/Lowercase)-sensitive
         
        if self.parser.doc.find('spatial', attrs={'xsi:type': 'dcterms:POINT'}):
            # <dcterms:spatial xsi:type="dcterms:POINT">9.811246,56.302585</dcterms:spatial>
            point = self.parser.doc.find('spatial', attrs={'xsi:type': 'dcterms:POINT'}).text.split(',')
            geometry = self._geometry_point(self, point)
            
        elif self.parser.doc.find('coverage', attrs={'xsi:type': 'dcterms:Point'}):
            # <dc:coverage xsi:type="dcterms:Point">east=-1.47; north=-78.82; elevation=5000;</dc:coverage>
            string_aux = self.parser.doc.find('spatial', attrs={'xsi:type': 'dcterms:Point'})
            point_dict = self._dc_item_to_dict(string_aux)
            point = (point_dict['north'],point_dict['east'])
            geometry = self._geometry_point(self, point)
            
        elif self.parser.doc.find('spatial', attrs={'xsi:type': 'DCTERMS:Box'}):
            # <dcterms:spatial xsi:type="DCTERMS:Box">37.2888 -32.27982 37.30134 -32.275618</dcterms:spatial>
            bbox = self.parser.doc.find('spatial', attrs={'xsi:type': 'DCTERMS:Box'}).text.split()
            geometry = self._geometry_bbox(self, bbox)
            
        elif self.parser.doc.find('coverage', attrs={''}):
           coverage = self.parser.doc.find('coverage', attrs={''})
           if  coverage. XXXXX
           # <dc:coverage>North 37.30134, South 37.2888, East -32.275618, West -32.27982</dc:coverage>
           bbox = self.parser.doc.find('spatial', attrs={'xsi:type': 'DCTERMS:Box'}).text.split() XXXXX
           geometry = self._geometry_bbox(self, bbox)
 
        else:
            geometry = None
        return geometry
