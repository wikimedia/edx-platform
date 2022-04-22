"""
WikiTransformer classes
"""
import re
from lxml import etree
from abc import ABC, abstractmethod

class WikiTransformer(ABC):
    """
    Abstract class with raw_data_to_meta_data and meta_data_to_raw_data functions
    Attributes:
        component_type (str) : Type of edx component i.e video, problem, etc
        data_type (str): Type of data stored in component i.e xml, html, list, etc
    """
    def __init__(self, component_type=None, data_type=None):
        self.component_type = component_type
        self.data_type = data_type

    @abstractmethod
    def validate_meta_data(self, data):
        """
        validate meta_data based on type of component
        """
        pass

    @abstractmethod
    def raw_data_to_meta_data(self, raw_data):
        """
        Customize this function based on the type of component
        Attributes:
            raw_data: (any) initial format of data retrieved from edx block,
                For Example, the problem is in XML string and video transcripts are in the list
        Returns:
            meta_data: (any) data after transforming raw_data. It differs from component to component
                For Example, problem meta_data contains encodings; encoding is a key-value pair,
                the key represents the position of text in XML and value represents text at that position
        Note: Go to problem transformer for more detail
        """
        pass

    @abstractmethod
    def meta_data_to_raw_data(self, meta_data):
        """
        Customize this function based on the type of component
        Attributes:
            meta_data: (dict) data needed to update initial data of a component
                For Example: problem meta_data contain xml_data and encodings.
                Using xml_data and encodings we can generate the updated XML with
                new encodings applied to the positions present in encodings.
        Returns:
            raw_data: updated data
                For Example: Using xml_data and encodings in meta_data,
                we can generate the updated XML string
        Note: Go to problem transformer for more detail
        """
        pass

class ProblemTransformer(WikiTransformer):
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
        data: (dict) data should have encodings and xml_data
        """
        if 'xml_data' not in data or 'encodings' not in data:
            raise Exception('xml_data and encodings are required in problem meta_data')
        return True

    def _convert_xpath_to_meta_key_format(self, path):
        """
        Converts xpath in specific key format as Meta server only allows '_', '.' and '-' for data keys.
        xpath: string in xpath format /problem/choiceresponse/checkboxgroup/choice[1]
        returns string in meta_key format i.e problem.choiceresponse.checkboxgroup.choice.1
        """
        converted_path = path.replace("/", ".")[1:]
        while True:
            match = re.search(r"\[\d\]", converted_path)
            if not match:
                break;
            start, end = match.span()
            converted_path = converted_path[:start] + "." + converted_path[end-2] + converted_path[end:]
        return converted_path

    def _convert_meta_key_format_to_xpath(self, key):
        """
        Converts meta key format to xpath.
        key: string in meta_key format i.e problem.choiceresponse.checkboxgroup.choice.1
        returns string in xpath format /problem/choiceresponse/checkboxgroup/choice[1]
        """
        converted_path = key
        while True:
            match = re.search(r"\.\d", converted_path)
            if not match:
                break;
            start, end = match.span()
            converted_path = converted_path[:start] + "[" + converted_path[end-1] + "]" + converted_path[end:]
        return "/{}".format(converted_path.replace('.','/'))

    def raw_data_to_meta_data(self, raw_data):
        """
        Convert raw_data of problem (xml) to the meta_data of problem component (dict)
        Arguments:
            raw_data: (str) xml-string
                sample => '''
                            <problem>
                                <multiplechoiceresponse>
                                    <p>Sample text p</p>
                                    <label>Sample text label</label>
                                    <choicegroup type="MultipleChoice">
                                    <choice correct="true">Sample text choice 1</choice>
                                    <choice correct="false">Sample text choice 2</choice>
                                    </choicegroup>
                                </multiplechoiceresponse>
                            </problem>
                        '''
        Returns:
            meta_data: (dict) - xml encoding
                sample =>
                    {
                        'problem.multiplechoiceresponse.choicegroup.choice[1]': 'Sample text choice 1',
                        'problem.multiplechoiceresponse.choicegroup.choice[2]': 'Sample text choice 2',
                        'problem.multiplechoiceresponse.label': 'Sample text label',
                        'problem.multiplechoiceresponse.p': 'Sample text p'
                    }

        """
        parser = etree.XMLParser(remove_blank_text=True)
        problem = etree.XML(raw_data, parser=parser)
        tree = etree.ElementTree(problem)
        data_dict = {}
        for e in problem.iter("*"):
            if e.text:
                # have to convert xpath as Meta server only allows '_', '.' and '-' for data keys.
                converted_xpath = self._convert_xpath_to_meta_key_format(tree.getpath(e))
                data_dict.update({converted_xpath: e.text})
        return data_dict

    def meta_data_to_raw_data(self, meta_data):
        """
        Convet meta_data of problem (dict) to the raw_data of problem (xml)
        Arguments:
            meta_data = (dict) { xml_data (str), encodings (dict) }
                sample => {
                    xml_data:  '''
                               <problem>
                                    <multiplechoiceresponse>
                                        <p>Sample text p</p>
                                        <label>Sample text label</label>
                                        <choicegroup type="MultipleChoice">
                                        <choice correct="true">Sample text choice 1</choice>
                                        <choice correct="false">Sample text choice 2</choice>
                                        </choicegroup>
                                    </multiplechoiceresponse>
                                </problem>
                                '''
                    encodings: {
                        'problem.multiplechoiceresponse.choicegroup.choice[1]': 'Updated text choice 1',
                        'problem.multiplechoiceresponse.choicegroup.choice[2]': 'Updated text choice 2',
                        'problem.multiplechoiceresponse.label': 'Updated text label',
                        'problem.multiplechoiceresponse.p': 'Updated text p'
                    }

                }
        Returns:
            raw_data: (str) xml-string
                sample => ''''
                            <problem>
                                <multiplechoiceresponse>
                                    <p>Updated text p</p>
                                    <label>Updated text label</label>
                                    <choicegroup type="MultipleChoice">
                                    <choice correct="true">Updated text choice 1</choice>
                                    <choice correct="false">Updated text choice 2</choice>
                                    </choicegroup>
                                </multiplechoiceresponse>
                            </problem>
                        ''''
        """
        if self.validate_meta_data(meta_data):
            xml_data = meta_data.get('xml_data')
            encodings = meta_data.get('encodings')
            parser = etree.XMLParser(remove_blank_text=True)
            problem = etree.XML(xml_data, parser=parser)
            for key, value in encodings.items():
                xpath = self._convert_meta_key_format_to_xpath(key)
                element = problem.xpath(xpath)
                if element:
                    element[0].text = value
                else:
                    raise Exception('{} not found in xml_data'.format(key))
        return etree.tostring(problem)

TRANSFORMER_CLASS_MAPPING = {
    # add custom transformers here
    'problem': ProblemTransformer,
}
