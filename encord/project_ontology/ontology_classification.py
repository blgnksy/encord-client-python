from dataclasses import dataclass
from typing import List

from encord.project_ontology.classification_attribute import ClassificationAttribute


@dataclass
class OntologyClassification:
    """
    A dataclass which holds classifications of the :class:`.Ontology`.
    """

    #: A unique (to the ontology) identifier of the classification.
    id: str
    #: An 8-character hex string uniquely defining the option.
    feature_node_hash: str
    #: A List of attributes for the classification.
    attributes: List[ClassificationAttribute]
