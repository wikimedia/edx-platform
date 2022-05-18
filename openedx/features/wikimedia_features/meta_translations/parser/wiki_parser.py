"""
WikiParser classes
"""
from lxml import etree
from abc import ABC, abstractmethod

class WikiParser(ABC):
    """
    Abstract class with raw_data_to_meta_data and meta_data_to_raw_data functions
    Attributes:
        component_type (str) : What is the type of edx component i.e video, problem, etc
        data_type (str): What is the type of data stored in component i.e xml, html, list, etc
    """
    def __init__(self, component_type=None, data_type=None):
        self.component_type = component_type
        self.data_type = data_type
    
    @abstractmethod
    def validate_meta_data(self, data):
        """
        validate meta_data based on type of component
        """
  
    @abstractmethod
    def raw_data_to_meta_data(self, raw_data):
        """
        customize this function based on the type of component
        """
        pass
  
    @abstractmethod
    def meta_data_to_raw_data(self, meta_data):
        """
        customize this function based on the type of component
        """
        pass

class ProblemParser(WikiParser):
    """
    Parser for problem type components i.e Multiple Choice, Checkbox etc
    The parser only parse xml problems
    Atributes:
        component_type = 'problem'
        data_type = 'xml'
    """
    def __init__(self):
        super().__init__(component_type='problem', data_type='xml')

    def validate_meta_data(self, data):
        """
        data should have encodings and xml_data
        """
        if 'xml_data' not in data or 'encodings' not in data:
            raise Exception('xml_data and encodings are required in problem meta_data')
        return True
  
    def raw_data_to_meta_data(self, raw_data):
        """
        Convert raw_data of problem (xml) to the meta_data of problem component (dict)
        Arguments:
            raw_data: (str) xml-string
        Returns:
            meta_data: (dict) { encodings (dict) }
        """
        parser = etree.XMLParser(remove_blank_text=True)
        problem = etree.XML(raw_data, parser=parser)
        tree = etree.ElementTree(problem)
        data_dict = {}
        for e in problem.iter("*"):
            if e.text:
                data_dict.update({tree.getpath(e).replace("/", ".")[1:]: e.text})
        return { 'encodings': data_dict }
  
    def meta_data_to_raw_data(self, meta_data):
        """
        Convet meta_data of problem (dict) to the raw_data of problem (xml)
        Arguments:
            meta_data = (dict) { xml_data (str), encodings (dict) }
        Returns:
            raw_data: (str) xml-string
        """
        if self.validate_meta_data(meta_data):
            xml_data = meta_data.get('xml_data')
            encodings = meta_data.get('encodings')
            parser = etree.XMLParser(remove_blank_text=True)
            problem = etree.XML(xml_data, parser=parser)
            for key, value in encodings.items():
                element = problem.xpath("/{}".format(key.replace('.','/')))
                if element:
                    element[0].text = value
                else:
                    raise Exception('{} now found in xml_data'.format(key))
        return etree.tostring(problem)
