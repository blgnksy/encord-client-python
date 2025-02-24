from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Sequence, Set, Union

from encord.exceptions import LabelRowError
from encord.objects.common import (
    Attribute,
    ChecklistAttribute,
    FlatOption,
    NestableOption,
    Option,
    OptionType,
    PropertyType,
    RadioAttribute,
    TextAttribute,
    _get_option_by_hash,
)
from encord.objects.constants import DEFAULT_MANUAL_ANNOTATION
from encord.objects.frames import Ranges, ranges_to_list
from encord.objects.utils import _lower_snake_case, short_uuid_str


class Answer(ABC):
    """An internal helper class for the LabelRowV2 class. This class is not meant to be used directly by users."""

    _ontology_attribute: Attribute

    def __init__(self, ontology_attribute: Attribute, track_hash: Optional[str] = None):
        self._answered = False
        self._ontology_attribute = ontology_attribute
        self._track_hash = track_hash or short_uuid_str()
        self._is_manual_annotation = DEFAULT_MANUAL_ANNOTATION
        self._should_propagate = False

    def is_answered(self) -> bool:
        return self._answered

    def unset(self) -> None:
        """Remove the value from the answer"""
        self._answered = False

    @property
    def is_dynamic(self) -> bool:
        return self._ontology_attribute.dynamic

    @is_dynamic.setter
    def is_dynamic(self, value: bool) -> NoReturn:
        raise RuntimeError("Cannot set the is_dynamic value of the answer.")

    @property
    def is_manual_annotation(self) -> bool:
        return self._is_manual_annotation

    @is_manual_annotation.setter
    def is_manual_annotation(self, value: bool) -> None:
        self._is_manual_annotation = value

    @property
    def ontology_attribute(self):
        return deepcopy(self._ontology_attribute)

    @ontology_attribute.setter
    def ontology_attribute(self, v: Any) -> NoReturn:
        raise RuntimeError("Cannot reset the ontology attribute of an instantiated answer.")

    def to_encord_dict(self, ranges: Optional[Ranges] = None) -> Optional[Dict]:
        """
        A low level helper to convert to the Encord JSON format.
        For most use cases the `get_answer` function should be used instead.
        """
        if not self.is_answered():
            return None

        ret = self._to_encord_dict_impl(self.is_dynamic)
        if self.is_dynamic:
            ret.update(self._get_encord_dynamic_fields(ranges))

        return ret

    @abstractmethod
    def _to_encord_dict_impl(self, is_dynamic: bool = False) -> Dict:
        pass

    @abstractmethod
    def from_dict(self, d: Dict) -> None:
        pass

    def _get_encord_dynamic_fields(self, ranges: Ranges) -> Dict:
        return {
            "dynamic": True,
            "range": ranges_to_list(ranges),
            "shouldPropagate": self._should_propagate,
            "trackHash": self._track_hash,
        }


class TextAnswer(Answer):
    def __init__(self, ontology_attribute: TextAttribute):
        super().__init__(ontology_attribute)
        self._value = None

    def set(self, value: str) -> TextAnswer:
        """Returns the object itself"""
        if not isinstance(value, str):
            raise ValueError("TextAnswer can only be set to a string.")
        self._value = value
        self._answered = True
        return self

    def get_value(self) -> Optional[str]:
        if not self.is_answered():
            return None
        else:
            return self._value

    def copy_from(self, text_answer: TextAnswer):
        if text_answer.ontology_attribute.feature_node_hash != self.ontology_attribute.feature_node_hash:
            raise ValueError(
                "Copying from a TextAnswer which is based on a different ontology Attribute is not possible."
            )
        other_is_answered = text_answer.is_answered()
        if not other_is_answered:
            self.unset()
        else:
            other_answer = text_answer.get_value()
            self.set(other_answer)

    def _to_encord_dict_impl(self, is_dynamic: bool = False) -> Dict:
        return {
            "name": self.ontology_attribute.name,
            "value": _lower_snake_case(self.ontology_attribute.name),
            "answers": self._value,
            "featureHash": self.ontology_attribute.feature_node_hash,
            "manualAnnotation": self.is_manual_annotation,
        }

    def from_dict(self, d: Dict) -> None:
        if d["featureHash"] != self.ontology_attribute.feature_node_hash:
            raise ValueError("Cannot set the value of a TextAnswer based on a different ontology attribute.")

        self._answered = True
        self.set(d["answers"])
        self.is_manual_annotation = d["manualAnnotation"]

    def __hash__(self):
        return hash((self._value, type(self).__name__))

    def __eq__(self, other: TextAnswer) -> bool:
        if not isinstance(other, TextAnswer):
            return False
        else:
            return self._value == other._value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"


@dataclass
class RadioAnswer(Answer):
    def __init__(self, ontology_attribute: RadioAttribute):
        super().__init__(ontology_attribute)
        self._value: Optional[NestableOption] = None

    def set(self, value: NestableOption):
        if not isinstance(value, NestableOption):
            raise ValueError("RadioAnswer can only be set to a NestableOption.")

        passed = False
        for child in self._ontology_attribute.options:
            if value.feature_node_hash == child.feature_node_hash:
                passed = True
        if not passed:
            raise ValueError(
                f"The supplied NestableOption `{value}` is not a child of the RadioAttribute that "
                f"is associated with this class: `{self._ontology_attribute}`"
            )
        self._answered = True
        self._value = value

    def get_value(self) -> Optional[NestableOption]:
        if not self.is_answered():
            return None
        else:
            return self._value

    def copy_from(self, radio_answer: RadioAnswer):
        if radio_answer.ontology_attribute.feature_node_hash != self.ontology_attribute.feature_node_hash:
            raise ValueError(
                "Copying from a RadioAnswer which is based on a different ontology Attribute is not possible."
            )
        other_is_answered = radio_answer.is_answered()
        if not other_is_answered:
            self.unset()
        else:
            other_answer = radio_answer.get_value()
            self.set(other_answer)

    def _to_encord_dict_impl(self, is_dynamic: bool = False) -> Optional[Dict]:
        nestable_option = self._value

        return {
            "name": self.ontology_attribute.name,
            "value": _lower_snake_case(self.ontology_attribute.name),
            "answers": [
                {
                    "name": nestable_option.label,
                    "value": nestable_option.value,
                    "featureHash": nestable_option.feature_node_hash,
                }
            ],
            "featureHash": self.ontology_attribute.feature_node_hash,
            "manualAnnotation": self.is_manual_annotation,
        }

    def from_dict(self, d: Dict) -> None:
        if d["featureHash"] != self.ontology_attribute.feature_node_hash:
            raise ValueError("Cannot set the value of a TextAnswer based on a different ontology attribute.")

        self._answered = True
        answers = d["answers"]
        if len(answers) != 1:
            raise ValueError("RadioAnswers must have exactly one answer.")

        answer = answers[0]
        nestable_option = _get_option_by_hash(answer["featureHash"], self.ontology_attribute.options)
        self.set(nestable_option)
        self.is_manual_annotation = d["manualAnnotation"]

    def __hash__(self):
        return hash((self._value, type(self).__name__))

    def __eq__(self, other: RadioAnswer) -> bool:
        if not isinstance(other, RadioAnswer):
            return False
        else:
            return self._value == other._value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"


@dataclass
class ChecklistAnswer(Answer):
    """
    Checkboxes behave slightly different from the other answer types. When the checkbox is unanswered, it will be
    the equivalent of not having selected any checkbox answer in the Encord platform.
    The initial state will be every checkbox unchecked.
    """

    def __init__(self, ontology_attribute: ChecklistAttribute):
        super().__init__(ontology_attribute)
        self._ontology_options_feature_hashes: Set[str] = self._initialise_ontology_options_feature_hashes()
        self._feature_hash_to_answer_map: Dict[str, bool] = self._initialise_feature_hash_to_answer_map()

    def check_options(self, values: Iterable[FlatOption]):
        self._answered = True
        for value in values:
            self._verify_flat_option(value)
            self._feature_hash_to_answer_map[value.feature_node_hash] = True

    def uncheck_options(self, values: Iterable[FlatOption]):
        self._answered = True
        for value in values:
            self._verify_flat_option(value)
            self._feature_hash_to_answer_map[value.feature_node_hash] = False

    def set_options(self, values: Iterable[FlatOption]):
        for value in values:
            if not isinstance(value, FlatOption):
                raise ValueError("ChecklistAnswer can only be set to FlatOptions.")

        self._answered = True
        for key in self._feature_hash_to_answer_map.keys():
            self._feature_hash_to_answer_map[key] = False
        for value in values:
            self._verify_flat_option(value)
            self._feature_hash_to_answer_map[value.feature_node_hash] = True

    def get_options(self) -> List[FlatOption]:
        if not self.is_answered():
            return []
        else:
            return [
                option
                for option in self._ontology_attribute.options
                if self._feature_hash_to_answer_map[option.feature_node_hash]
            ]

    def get_value(self, value: FlatOption) -> bool:
        return self._feature_hash_to_answer_map[value.feature_node_hash]

    def copy_from(self, checklist_answer: ChecklistAnswer):
        if checklist_answer.ontology_attribute.feature_node_hash != self.ontology_attribute.feature_node_hash:
            raise ValueError(
                "Copying from a ChecklistAnswer which is based on a different ontology Attribute is not possible."
            )
        other_is_answered = checklist_answer.is_answered()
        if not other_is_answered:
            self.unset()
        else:
            self._answered = True
            for feature_node_hash in self._feature_hash_to_answer_map.keys():
                option = _get_option_by_hash(feature_node_hash, self.ontology_attribute.options)
                other_answer = checklist_answer.get_value(option)
                self._feature_hash_to_answer_map[feature_node_hash] = other_answer

    def _initialise_feature_hash_to_answer_map(self) -> Dict[str, bool]:
        ret: Dict[str, bool] = {}
        for child in self._ontology_attribute.options:
            ret[child.feature_node_hash] = False
        return ret

    def _initialise_ontology_options_feature_hashes(self) -> Set[str]:
        ret: Set[str] = set()
        for child in self._ontology_attribute.options:
            ret.add(child.feature_node_hash)
        return ret

    def _verify_flat_option(self, value: FlatOption) -> None:
        if value.feature_node_hash not in self._ontology_options_feature_hashes:
            raise RuntimeError(
                f"The supplied FlatOption `{value}` is not a child of the ChecklistAttribute that "
                f"is associated with this class: `{self._ontology_attribute}`"
            )

    def _to_encord_dict_impl(self, is_dynamic: bool = False) -> Optional[Dict]:
        checked_options = []
        ontology_attribute: ChecklistAttribute = self._ontology_attribute
        for option in ontology_attribute.options:
            if self.get_value(option):
                checked_options.append(option)

        answers = []
        for option in checked_options:
            answers.append(
                {
                    "name": option.label,
                    "value": option.value,
                    "featureHash": option.feature_node_hash,
                }
            )
        return {
            "name": self.ontology_attribute.name,
            "value": _lower_snake_case(self.ontology_attribute.name),
            "answers": answers,
            "featureHash": self.ontology_attribute.feature_node_hash,
            "manualAnnotation": self.is_manual_annotation,
        }

    def from_dict(self, d: Dict) -> None:
        if d["featureHash"] != self.ontology_attribute.feature_node_hash:
            raise ValueError("Cannot set the value of a ChecklistAnswer based on a different ontology attribute.")

        answers = d["answers"]
        if len(answers) == 0:
            return

        for answer in answers:
            flat_option = _get_option_by_hash(answer["featureHash"], self.ontology_attribute.options)
            self.check_options([flat_option])

        self.is_manual_annotation = d["manualAnnotation"]
        self._answered = True

    def __hash__(self):
        flat_values = [(key, value) for key, value in self._feature_hash_to_answer_map.items()]
        flat_values.sort()
        return hash((tuple(flat_values), type(self).__name__))

    def __eq__(self, other: ChecklistAnswer) -> bool:
        if not isinstance(other, ChecklistAnswer):
            return False
        else:
            flat_values = {(key, value) for key, value in self._feature_hash_to_answer_map.items()}
            other_flat_values = {(key, value) for key, value in other._feature_hash_to_answer_map.items()}
            return flat_values == other_flat_values

    def __repr__(self):
        flat_values = [(key, value) for key, value in self._feature_hash_to_answer_map.items()]
        return f"{self.__class__.__name__}({flat_values})"


def get_default_answer_from_attribute(attribute: Attribute) -> Answer:
    property_type = attribute.get_property_type()
    if property_type == PropertyType.TEXT:
        return TextAnswer(attribute)
    elif property_type == PropertyType.RADIO:
        return RadioAnswer(attribute)
    elif property_type == PropertyType.CHECKLIST:
        return ChecklistAnswer(attribute)
    else:
        raise RuntimeError(f"Got an attribute with an unexpected property type: {attribute}")


def set_answer_for_object(answer_object: Answer, answer_value: Union[str, Option, Iterable[Option]]) -> None:
    attribute = answer_object.ontology_attribute
    if isinstance(attribute, TextAttribute):
        answer_object.set(answer_value)
    elif isinstance(attribute, RadioAttribute):
        answer_object.set(answer_value)
    elif isinstance(attribute, ChecklistAttribute):
        answer_object.set_options(answer_value)
    else:
        raise ValueError(f"Unknown attribute type: {type(attribute)}")


def get_answer_from_object(answer_object: Answer) -> Union[str, Option, Iterable[Option], None]:
    attribute = answer_object.ontology_attribute
    if isinstance(attribute, TextAttribute):
        return answer_object.get_value()
    elif isinstance(attribute, RadioAttribute):
        return answer_object.get_value()
    elif isinstance(attribute, ChecklistAttribute):
        return answer_object.get_options()
    else:
        raise ValueError(f"Unknown attribute type: {type(attribute)}")


def _get_default_static_answers_from_attributes(attributes: List[Attribute]) -> List[Answer]:
    ret: List[Answer] = list()
    for attribute in attributes:
        if not attribute.dynamic:
            answer = get_default_answer_from_attribute(attribute)
            ret.append(answer)

        if attribute.has_options_field():
            for option in attribute.options:
                if option.get_option_type() == OptionType.NESTABLE:
                    other_attributes = _get_default_static_answers_from_attributes(option.nested_options)
                    ret.extend(other_attributes)

    return ret


def _get_static_answer_map(attributes: List[Attribute]) -> Dict[str, Answer]:
    answers = _get_default_static_answers_from_attributes(attributes)
    answer_map = {answer.ontology_attribute.feature_node_hash: answer for answer in answers}
    return answer_map


def _search_child_attributes(
    passed_attribute: Attribute, search_attribute: Attribute, static_answer_map: Dict[str, Answer]
) -> bool:
    if passed_attribute == search_attribute:
        return True

    if not isinstance(search_attribute, RadioAttribute):
        return False

    answer = static_answer_map[search_attribute.feature_node_hash]
    value = answer.get_value()
    if value is None:
        return False

    for option in search_attribute.options:
        if value == option:
            for nested_option in option.nested_options:
                # If I have multi nesting here, what then?
                if _search_child_attributes(passed_attribute, nested_option, static_answer_map):
                    return True

    return False


def _search_for_parent(passed_option: Option, attributes: List[Attribute]) -> Optional[Attribute]:
    for attribute in attributes:
        if attribute.has_options_field():
            for option in attribute.options:
                if option == passed_option:
                    return attribute
                if option.get_option_type() == OptionType.NESTABLE:
                    attribute_opt = _search_for_parent(passed_option, option.nested_options)
                    if attribute_opt is not None:
                        return attribute_opt
    return None


def _search_for_text_attributes(attributes: List[Attribute]) -> List[Attribute]:
    text_attributes: List[Attribute] = list()
    for attribute in attributes:
        if attribute.get_property_type() == PropertyType.TEXT:
            text_attributes.append(attribute)
        elif attribute.has_options_field():
            for option in attribute.options:
                if option.get_option_type() == OptionType.NESTABLE:
                    text_attributes.extend(_search_for_text_attributes(option.nested_options))
    return text_attributes


def _infer_attribute_from_answer(
    attributes: List[Attribute], answer: Union[str, Option, Sequence[Option]]
) -> Attribute:
    if isinstance(answer, Option):
        parent_opt = _search_for_parent(answer, attributes)  # type: ignore
        if parent_opt is None:
            raise LabelRowError(
                "Cannot find a corresponding attribute for the given answer in the Object ontology. "
                "Please ensure to only pass the correct answer options for the given Object ontology. "
                f"The used answer is `{answer}`"
            )
        return parent_opt

    elif isinstance(answer, str):
        text_attributes = _search_for_text_attributes(attributes)
        if len(text_attributes) == 0:
            raise LabelRowError(
                "Cannot find any text attribute in the ontology of the given instance. Setting "
                "a text answer is not supported."
            )
        if len(text_attributes) > 1:
            raise LabelRowError(
                "Multiple text attributes are present in the ontology of the given instance. "
                f"Please provide the attribute explicitly. The found text attributes are {text_attributes}"
            )
        return text_attributes[0]

    elif isinstance(answer, Sequence):
        if len(answer) == 0:
            raise LabelRowError(
                "Cannot infer the attribute if a list of answers is empty. Please provide the " "attribute explicitly."
            )

        parent_opt = _search_for_parent(answer[0], attributes)
        if parent_opt is None:
            raise LabelRowError(
                "Cannot find a corresponding attribute for one of the given answers in the Object ontology. "
                "Please ensure to only pass the correct answer options for the given Object ontology. "
                f"The used answer is `{answer}`"
            )
        for option in answer:
            if option not in parent_opt.options:
                raise LabelRowError(
                    "Multiple options have been provided that do not belong to the same attribute. Please ensure that "
                    "all options belong to the same ontology attribute."
                )
        return parent_opt

    else:
        raise NotImplementedError(f"The answer type is not supported for answer `{answer}` of type {type(answer)}.")
