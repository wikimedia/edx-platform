"""
Mappping-related exceptions.
"""


class MultipleObjectsFoundInMappingCreation(Exception):
    """
    Exception raised when multiple components of base course returned in target block mapping creation.
    """
    def __init__(self, message="Multiple objects returned in Mapping creation.", block_id=None):
        self.message = message
        self.block_id = block_id
        super().__init__(self.message)
